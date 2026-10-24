"""Root-only, real Mininet/OVS end-to-end check. Start Ryu first."""

import datetime
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.log import lg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from topology import FirewallTopo


ROOT = pathlib.Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "screenshots" / "terminal-evidence"
REPORT = ROOT / "reports" / "integration-results.json"
API = "http://127.0.0.1:8080"


def save(name, content):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(content)


def request(path, method="GET"):
    with urllib.request.urlopen(urllib.request.Request(API + path, method=method), timeout=5) as response:
        return json.loads(response.read()), response.status


def expect_http_error(path, method, expected):
    try:
        request(path, method)
    except urllib.error.HTTPError as error:
        body = json.loads(error.read())
        assert error.code == expected, (error.code, body)
        return {"status": error.code, "body": body}
    raise AssertionError(f"Expected HTTP {expected} for {method} {path}")


def flows():
    return subprocess.check_output(
        ["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", "s1"],
        text=True, stderr=subprocess.STDOUT)


def drop_count(text):
    return sum("priority=100" in line and "actions=drop" in line for line in text.splitlines())


def has_client_drop(text, direction):
    labels = (f"ipv4_{direction}=10.0.0.2", f"nw_{direction}=10.0.0.2")
    return any("priority=100" in line and "actions=drop" in line
               and any(label in line for label in labels)
               for line in text.splitlines())


def ping(net, source, target, label):
    proc = net.get(source).popen(
        ["ping", "-c", "3", "-W", "1", f"10.0.0.{target[1:]}"] ,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output, _ = proc.communicate(timeout=10)
    save(label + ".txt", f"$ {source} ping -c 3 -W 1 10.0.0.{target[1:]}\n" + output)
    loss = re.search(r"(\d+(?:\.\d+)?)% packet loss", output)
    return {"success": proc.returncode == 0, "packet_loss_percent": float(loss.group(1)) if loss else None,
            "evidence": label + ".txt"}


def ping_all(net, label):
    output = io.StringIO()
    original = lg.ch.stream
    lg.ch.stream = output
    try:
        loss = net.pingAll()
    finally:
        lg.ch.stream = original
    save(label + ".txt", output.getvalue() + f"\nMeasured packet loss: {loss}%\n")
    print(output.getvalue(), end="")
    return loss


def wait_for_flow(should_exist, timeout=4):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        dump = flows()
        source = has_client_drop(dump, "src")
        target = has_client_drop(dump, "dst")
        if (source and target) == should_exist and (not should_exist or drop_count(dump) >= 2):
            return dump
        time.sleep(0.05)
    raise AssertionError("OpenFlow drop state did not match expected value")


def main():
    if os.geteuid() != 0:
        raise SystemExit("Run as root: sudo /usr/bin/python3 tests/run_integration.py")
    results = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "tests": {}, "measurements": {}}
    net = None
    blocked = False
    try:
        net = Mininet(topo=FirewallTopo(), controller=None, switch=OVSSwitch, autoSetMacs=True)
        net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
        net.start()
        if not net.waitConnected(timeout=10):
            raise AssertionError("s1 did not connect to Ryu")
        topology = {"hosts": sorted(h.name for h in net.hosts),
                    "switches": sorted(s.name for s in net.switches),
                    "links": sorted(str(link) for link in net.links),
                    "protocols": subprocess.check_output(["ovs-vsctl", "get", "bridge", "s1", "protocols"], text=True).strip()}
        save("02_topology.json", json.dumps(topology, indent=2))
        assert topology["hosts"] == ["h1", "h2", "h3"]
        assert topology["switches"] == ["s1"]
        assert "OpenFlow13" in topology["protocols"]
        results["tests"]["topology"] = topology

        baseline = {pair: ping(net, pair[:2], pair[2:], "03_baseline_" + pair)
                    for pair in ("h1h2", "h1h3", "h2h3", "h3h1")}
        baseline_loss = ping_all(net, "03_baseline_all_hosts")
        assert all(item["packet_loss_percent"] == 0 for item in baseline.values())
        assert baseline_loss == 0, baseline_loss
        results["tests"]["baseline"] = baseline
        results["measurements"]["baseline_loss_percent"] = baseline_loss
        before = flows()
        save("03_flows_before.txt", before)
        results["measurements"]["drop_rules_before"] = drop_count(before)
        assert drop_count(before) == 0, "Unexpected firewall drop before blocking"
        initial, _ = request("/firewall/blocked")
        save("04_initial_blocked.json", json.dumps(initial, indent=2))
        assert initial == {"blocked_ips": [], "switch_connected": True}, initial

        started = time.monotonic()
        response, status = request("/firewall/block/10.0.0.2", "POST")
        blocked = True
        during = wait_for_flow(True)
        results["measurements"]["block_to_verified_flow_seconds"] = round(time.monotonic() - started, 4)
        assert status == 200 and response["blocked"] is True
        save("05_block_response.json", json.dumps(response, indent=2))
        listing, _ = request("/firewall/blocked")
        assert listing["blocked_ips"] == ["10.0.0.2"]
        save("05_blocked_list.json", json.dumps(listing, indent=2))
        duplicate = expect_http_error("/firewall/block/10.0.0.2", "POST", 409)
        save("05_duplicate_block.json", json.dumps(duplicate, indent=2))
        results["tests"]["duplicate_block"] = duplicate
        save("07_flows_during.txt", during)
        results["measurements"]["drop_rules_during"] = drop_count(during)
        blocked_pings = {pair: ping(net, pair[:2], pair[2:], "06_during_" + pair)
                         for pair in ("h1h2", "h3h2", "h2h1", "h1h3")}
        assert blocked_pings["h1h2"]["packet_loss_percent"] == 100
        assert blocked_pings["h3h2"]["packet_loss_percent"] == 100
        assert blocked_pings["h2h1"]["packet_loss_percent"] == 100
        assert blocked_pings["h1h3"]["packet_loss_percent"] == 0
        results["tests"]["blocked_pings"] = blocked_pings

        started = time.monotonic()
        response, status = request("/firewall/unblock/10.0.0.2", "POST")
        blocked = False
        after = wait_for_flow(False)
        results["measurements"]["unblock_to_verified_removal_seconds"] = round(time.monotonic() - started, 4)
        assert status == 200 and response["blocked"] is False
        save("08_unblock_response.json", json.dumps(response, indent=2))
        listing, _ = request("/firewall/blocked")
        assert listing["blocked_ips"] == []
        save("08_unblocked_list.json", json.dumps(listing, indent=2))
        repeated = expect_http_error("/firewall/unblock/10.0.0.2", "POST", 404)
        save("08_repeated_unblock.json", json.dumps(repeated, indent=2))
        results["tests"]["repeated_unblock"] = repeated
        save("08_flows_after.txt", after)
        results["measurements"]["drop_rules_after"] = drop_count(after)
        assert drop_count(after) == 0, "Firewall drops remain after unblocking"
        recovery = {pair: ping(net, pair[:2], pair[2:], "09_recovery_" + pair)
                    for pair in ("h1h2", "h3h2", "h2h1")}
        recovery_loss = ping_all(net, "09_recovery_all_hosts")
        assert all(item["packet_loss_percent"] == 0 for item in recovery.values())
        assert recovery_loss == 0
        results["tests"]["recovery"] = recovery
        results["measurements"]["recovery_loss_percent"] = recovery_loss
        results["status"] = "PASS"
    except Exception as exc:
        results["status"] = "FAIL"
        results["error"] = repr(exc)
        raise
    finally:
        if blocked:
            try:
                request("/firewall/unblock/10.0.0.2", "POST")
            except Exception:
                pass
        if net is not None:
            net.stop()
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(results, indent=2) + "\n")
        print(f"Integration result: {results['status']}; report: {REPORT}")


if __name__ == "__main__":
    main()
