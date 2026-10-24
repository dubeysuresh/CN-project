# Dynamic Firewall and SDN Controller

Ryu 4.34 controls one Open vSwitch (`s1`) using OpenFlow 1.3. The switch has three Mininet hosts: `h1` (`10.0.0.1`), `h2` (`10.0.0.2`), and `h3` (`10.0.0.3`). The REST API changes high-priority IPv4 drop rules without restarting Mininet.

## Start

On Ubuntu, install Mininet and OVS with `sudo apt-get install mininet openvswitch-switch` and start the service with `sudo systemctl start openvswitch-switch`. Python 3.11 is required for the controller setup. The existing environment is `../.venv`. To prepare it again, run `bash scripts/bootstrap.sh`. This pins Ryu's build tooling and applies the Ryu/Eventlet WSGI compatibility fix inside the environment.

Terminal 1, from this directory:

```bash
bash scripts/run_controller.sh
```

Terminal 2 (Mininet requires root):

```bash
sudo mn --custom topology.py --topo firewalltopo \
  --switch ovsk,protocols=OpenFlow13 \
  --controller remote,ip=127.0.0.1,port=6653
```

At the `mininet>` prompt, first run `nodes`, `net`, and `pingall`. Verify baseline connectivity before making any block request.

Terminal 3:

```bash
curl -s http://127.0.0.1:8080/firewall/blocked
curl -s -X POST http://127.0.0.1:8080/firewall/block/10.0.0.2
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
curl -s -X POST http://127.0.0.1:8080/firewall/unblock/10.0.0.2
```

While blocked, test `h1 ping -c 3 h2`, `h3 ping -c 3 h2`, and `h1 ping -c 3 h3` at the Mininet prompt. The first two should fail; the last should succeed. After unblocking, repeat them and `pingall`.

## Repeatable tests

Unit tests work without root:

```bash
../.venv/bin/python -m unittest discover -s tests -v
```

For the complete real-network test, leave the controller running in Terminal 1 and run from this directory:

```bash
sudo /usr/bin/python3 tests/run_integration.py
```

The integration runner creates and removes Mininet's topology, tests the baseline **before** blocking, checks API responses and both OVS drop rules, measures block and removal latency, verifies isolation, and saves raw evidence to `screenshots/terminal-evidence/` and measurements to `reports/integration-results.json`. It stops immediately if the baseline fails.

The integration runner uses Ubuntu's `/usr/bin/python3` because apt installs Mininet into the system Python; Ryu continues to use `../.venv`.

## API

| Method | Path | Success | Common errors |
|---|---|---|---|
| GET | `/firewall/blocked` | `{"blocked_ips": [], "switch_connected": false}` | — |
| POST | `/firewall/block/{ip}` | `{"ip":"10.0.0.2","blocked":true,"switch":"s1"}` | 400 invalid/unconfigured; 409 duplicate; 503 switch unavailable |
| POST | `/firewall/unblock/{ip}` | `{"ip":"10.0.0.2","blocked":false,"switch":"s1"}` | 400 invalid/unconfigured; 404 not blocked; 503 switch unavailable |

Only `10.0.0.1`, `.2`, and `.3` are accepted as clients. A block installs **two** priority-100 IPv4 drop rules: source and destination. This makes inbound pings to the blocked client fail too. ARP and other non-IPv4 traffic remain outside this policy. The switch's `NORMAL` action supplies ordinary L2 forwarding below the drop priority.

See the [HTML project report](../project_doc/index.html) for the architecture, design choices, topology theory, actual test results, evidence, troubleshooting, and limits.
