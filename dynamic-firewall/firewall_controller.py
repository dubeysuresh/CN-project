"""OpenFlow 1.3 firewall for the three-host Mininet laboratory topology."""

import ipaddress
import json

from ryu.app.wsgi import ControllerBase, Response, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, DEAD_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3


NETWORK = ipaddress.ip_network("10.0.0.0/24")
CLIENTS = {ipaddress.ip_address(f"10.0.0.{n}") for n in (1, 2, 3)}
DROP_PRIORITY = 100
DROP_COOKIE_PREFIX = 0xF100000000000000
BARRIER_TIMEOUT = 3


class FirewallError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def parse_client(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise FirewallError(400, "Invalid IPv4 address") from exc
    if address.version != 4:
        raise FirewallError(400, "Only IPv4 addresses are supported")
    if address not in NETWORK:
        raise FirewallError(400, "Address is outside 10.0.0.0/24")
    if address not in CLIENTS:
        raise FirewallError(400, "Address is not one of the configured clients")
    return address


class DynamicFirewall(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {"wsgi": WSGIApplication}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datapath = None
        self.blocked = set()
        self.lock = hub.Semaphore(1)
        self.pending_barriers = {}
        self.errors = {}
        kwargs["wsgi"].register(FirewallRestController, {"firewall_app": self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        if dp.id != 1:
            self.logger.error("Rejecting unexpected datapath %s; expected s1 DPID 1", dp.id)
            return
        self.datapath = dp
        parser = dp.ofproto_parser
        # Remove this controller's stale rules after a controller restart.
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, cookie=DROP_COOKIE_PREFIX,
            cookie_mask=0xff00000000000000, table_id=0,
            command=dp.ofproto.OFPFC_DELETE,
            out_port=dp.ofproto.OFPP_ANY, out_group=dp.ofproto.OFPG_ANY,
            match=parser.OFPMatch()))
        # OVS performs ordinary L2 switching. High-priority IP drops override it.
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, priority=0, match=parser.OFPMatch(),
            instructions=[parser.OFPInstructionActions(
                dp.ofproto.OFPIT_APPLY_ACTIONS,
                [parser.OFPActionOutput(dp.ofproto.OFPP_NORMAL)])]))
        for address in sorted(self.blocked):
            self._send_drop(dp, address, add=True)
        dp.send_msg(parser.OFPBarrierRequest(dp))
        self.logger.info("s1 connected; normal forwarding and %d block policies sent", len(self.blocked))

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change(self, ev):
        if ev.state == DEAD_DISPATCHER and self.datapath is ev.datapath:
            self.datapath = None
            for event in self.pending_barriers.values():
                event.set()
            self.logger.warning("s1 disconnected; policy changes unavailable until reconnection")

    @set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
    def barrier_reply(self, ev):
        event = self.pending_barriers.get(ev.msg.xid)
        if event is not None:
            event.set()

    @set_ev_cls(ofp_event.EventOFPErrorMsg, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def openflow_error(self, ev):
        msg = ev.msg
        self.errors[msg.xid] = "OpenFlow error type=%s code=%s" % (msg.type, msg.code)
        self.logger.error("Switch rejected request xid=%s: %s", msg.xid, self.errors[msg.xid])

    def _send_drop(self, dp, address, add):
        parser = dp.ofproto_parser
        ofp = dp.ofproto
        xids = []
        for direction, field in enumerate(("ipv4_src", "ipv4_dst")):
            match = parser.OFPMatch(eth_type=0x0800, **{field: str(address)})
            cookie = DROP_COOKIE_PREFIX | (int(address) << 1) | direction
            if add:
                mod = parser.OFPFlowMod(
                    datapath=dp, cookie=cookie, table_id=0,
                    command=ofp.OFPFC_ADD, priority=DROP_PRIORITY,
                    match=match, instructions=[])
            else:
                mod = parser.OFPFlowMod(
                    datapath=dp, cookie=cookie, cookie_mask=0xffffffffffffffff,
                    table_id=0, command=ofp.OFPFC_DELETE_STRICT,
                    out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                    priority=DROP_PRIORITY, match=match)
            dp.send_msg(mod)
            xids.append(mod.xid)
        return xids

    def _apply(self, address, add):
        dp = self.datapath
        if dp is None:
            raise FirewallError(503, "s1 is not connected to the controller")
        xids = self._send_drop(dp, address, add)
        barrier = dp.ofproto_parser.OFPBarrierRequest(dp)
        dp.set_xid(barrier)
        done = hub.Event()
        self.pending_barriers[barrier.xid] = done
        try:
            dp.send_msg(barrier)
            if not done.wait(BARRIER_TIMEOUT) or self.datapath is not dp:
                raise FirewallError(503, "Timed out waiting for the switch to apply rules")
            failures = [self.errors.pop(x, None) for x in xids]
            failures = [failure for failure in failures if failure]
            if failures:
                raise FirewallError(503, "; ".join(failures))
        finally:
            self.pending_barriers.pop(barrier.xid, None)
            for xid in xids:
                self.errors.pop(xid, None)

    def change_block(self, value, add):
        address = parse_client(value)
        with self.lock:
            present = address in self.blocked
            if add and present:
                raise FirewallError(409, "Client is already blocked")
            if not add and not present:
                raise FirewallError(404, "Client is not blocked")
            self._apply(address, add)
            if add:
                self.blocked.add(address)
            else:
                self.blocked.remove(address)
            self.logger.info("%s client %s", "Blocked" if add else "Unblocked", address)
            return {"ip": str(address), "blocked": add, "switch": "s1"}


class FirewallRestController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.firewall = data["firewall_app"]

    @staticmethod
    def _json(payload, status=200):
        return Response(body=json.dumps(payload), content_type="application/json", status=status)

    @route("firewall", "/firewall/blocked", methods=["GET"])
    def get_blocked(self, req, **kwargs):
        return self._json({"blocked_ips": sorted(map(str, self.firewall.blocked)),
                           "switch_connected": self.firewall.datapath is not None})

    @route("firewall", "/firewall/block/{ip}", methods=["POST"])
    def block(self, req, ip, **kwargs):
        try:
            return self._json(self.firewall.change_block(ip, True))
        except FirewallError as exc:
            return self._json({"error": str(exc)}, exc.status)

    @route("firewall", "/firewall/unblock/{ip}", methods=["POST"])
    def unblock(self, req, ip, **kwargs):
        try:
            return self._json(self.firewall.change_block(ip, False))
        except FirewallError as exc:
            return self._json({"error": str(exc)}, exc.status)
