
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (
    CONFIG_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls,
)
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4


class DynamicFirewall(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # Example policy for an isolated test network.
    BLOCKED_IPS = {"10.0.0.3"}

    def __init__(self, *args, **kwargs):
        super(DynamicFirewall, self).__init__(*args, **kwargs)
        self.datapaths = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        self.datapaths[datapath.id] = datapath

        # Default rule: send unmatched packets to the controller.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER,
            )
        ]

        self.add_flow(
            datapath,
            priority=0,
            match=match,
            actions=actions,
        )

        self.logger.info(
            "Switch %s connected; default controller rule installed",
            datapath.id,
        )

    def add_flow(self, datapath, priority, match, actions):
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        instructions = []

        if actions:
            instructions = [
                parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS,
                    actions,
                )
            ]

        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
        )

        datapath.send_msg(mod)

    def install_block_rule(self, datapath, source_ip):
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=source_ip,
        )

        # Empty action list means matching packets are dropped.
        self.add_flow(
            datapath,
            priority=100,
            match=match,
            actions=[],
        )

        self.logger.warning(
            "BLOCK RULE installed for source IP %s",
            source_ip,
        )

    def install_allow_rule(self, datapath, source_ip):
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(
            eth_type=0x0800,
            ipv4_src=source_ip,
        )

        # Explicit allow rule: forward matching packets normally.
        actions = [
            parser.OFPActionOutput(
                datapath.ofproto.OFPP_NORMAL
            )
        ]

        self.add_flow(
            datapath,
            priority=50,
            match=match,
            actions=actions,
        )

        self.logger.info(
            "ALLOW RULE installed for source IP %s",
            source_ip,
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        ip_header = pkt.get_protocol(ipv4.ipv4)

        if ip_header is None:
            # This starter implementation handles IPv4 only.
            actions = [
                parser.OFPActionOutput(ofproto.OFPP_NORMAL)
            ]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=msg.match["in_port"],
                actions=actions,
                data=(
                    None
                    if msg.buffer_id != ofproto.OFP_NO_BUFFER
                    else msg.data
                ),
            )
            datapath.send_msg(out)
            return

        source_ip = ip_header.src
        destination_ip = ip_header.dst

        if source_ip in self.BLOCKED_IPS:
            self.install_block_rule(datapath, source_ip)
            self.logger.warning(
                "BLOCKED IPv4 packet %s -> %s",
                source_ip,
                destination_ip,
            )
            return

        self.logger.info(
            "ALLOWED IPv4 packet %s -> %s",
            source_ip,
            destination_ip,
        )

        # Forward through OVS's normal switching behavior.
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_NORMAL)
        ]

        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=msg.match["in_port"],
            actions=actions,
            data=(
                None
                if msg.buffer_id != ofproto.OFP_NO_BUFFER
                else msg.data
            ),
        )

        datapath.send_msg(out)
