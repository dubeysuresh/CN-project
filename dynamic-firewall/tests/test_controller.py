"""Checks rule construction and policy validation without root privileges."""

import importlib.util
import pathlib
from types import SimpleNamespace
import unittest

from ryu.ofproto import ofproto_v1_3, ofproto_v1_3_parser
from ryu.lib import hub


SOURCE = pathlib.Path(__file__).resolve().parents[1] / "firewall_controller.py"
spec = importlib.util.spec_from_file_location("firewall_controller", SOURCE)
firewall = importlib.util.module_from_spec(spec)
spec.loader.exec_module(firewall)


class FakeDatapath:
    id = 1
    ofproto = ofproto_v1_3
    ofproto_parser = ofproto_v1_3_parser

    def __init__(self):
        self.messages = []
        self.next_xid = 1

    def send_msg(self, message):
        if message.xid is None:
            self.set_xid(message)
        self.messages.append(message)

    def set_xid(self, message):
        message.set_xid(self.next_xid)
        self.next_xid += 1


class FakeWsgi:
    def register(self, *args):
        pass


class FirewallTests(unittest.TestCase):
    def setUp(self):
        self.app = firewall.DynamicFirewall(wsgi=FakeWsgi())
        self.dp = FakeDatapath()

    def test_client_validation(self):
        self.assertEqual(str(firewall.parse_client("10.0.0.2")), "10.0.0.2")
        for address in ("bad", "2001:db8::2", "10.0.1.2", "10.0.0.4"):
            with self.subTest(address=address), self.assertRaises(firewall.FirewallError):
                firewall.parse_client(address)

    def test_bidirectional_drop_rules_and_exact_deletion(self):
        address = firewall.parse_client("10.0.0.2")
        self.app._send_drop(self.dp, address, True)
        source, destination = self.dp.messages
        self.assertEqual(source.priority, 100)
        self.assertEqual(source.match["ipv4_src"], "10.0.0.2")
        self.assertEqual(destination.match["ipv4_dst"], "10.0.0.2")
        self.assertEqual(source.instructions, [])
        self.assertEqual(destination.instructions, [])
        self.assertEqual(source.command, ofproto_v1_3.OFPFC_ADD)
        self.app._send_drop(self.dp, address, False)
        for add, delete in zip(self.dp.messages[:2], self.dp.messages[2:]):
            self.assertEqual(delete.command, ofproto_v1_3.OFPFC_DELETE_STRICT)
            self.assertEqual(delete.cookie, add.cookie)
            self.assertEqual(dict(delete.match.items()), dict(add.match.items()))

    def test_no_switch_does_not_change_policy(self):
        with self.assertRaises(firewall.FirewallError) as caught:
            self.app.change_block("10.0.0.2", True)
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(self.app.blocked, set())

    def test_duplicate_and_missing_policy_errors(self):
        address = firewall.parse_client("10.0.0.2")
        self.app.blocked.add(address)
        with self.assertRaises(firewall.FirewallError) as duplicate:
            self.app.change_block("10.0.0.2", True)
        self.assertEqual(duplicate.exception.status, 409)
        with self.assertRaises(firewall.FirewallError) as missing:
            self.app.change_block("10.0.0.3", False)
        self.assertEqual(missing.exception.status, 404)

    def test_policy_updates_after_switch_barrier(self):
        self.app.datapath = self.dp
        def reply():
            for event in self.app.pending_barriers.values():
                event.set()
        hub.spawn_after(0.01, reply)
        response = self.app.change_block("10.0.0.2", True)
        self.assertTrue(response["blocked"])
        self.assertEqual(list(map(str, self.app.blocked)), ["10.0.0.2"])
        hub.spawn_after(0.01, reply)
        response = self.app.change_block("10.0.0.2", False)
        self.assertFalse(response["blocked"])
        self.assertEqual(self.app.blocked, set())

    def test_reconnect_replays_policy_above_normal_forwarding(self):
        self.app.blocked.add(firewall.parse_client("10.0.0.2"))
        self.app.switch_features(SimpleNamespace(msg=SimpleNamespace(datapath=self.dp)))
        stale_delete, normal, source_drop, destination_drop, barrier = self.dp.messages
        self.assertEqual(stale_delete.command, ofproto_v1_3.OFPFC_DELETE)
        self.assertEqual(normal.priority, 0)
        self.assertEqual(normal.instructions[0].actions[0].port, ofproto_v1_3.OFPP_NORMAL)
        self.assertEqual(source_drop.priority, 100)
        self.assertEqual(destination_drop.priority, 100)
        self.assertIsInstance(barrier, ofproto_v1_3_parser.OFPBarrierRequest)


if __name__ == "__main__":
    unittest.main()
