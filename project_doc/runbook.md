# Reproducible runbook

On Ubuntu, ensure Mininet and Open vSwitch are installed and the OVS service is active:

```bash
sudo apt-get install mininet openvswitch-switch
sudo systemctl start openvswitch-switch
```

Use the existing environment at `/home/suresh/project/.venv`. The setup script is repeatable and can recreate it with Python 3.11:

```bash
cd /home/suresh/project/dynamic-firewall
bash scripts/bootstrap.sh
../.venv/bin/python -m unittest discover -s tests -v
```

Run Ryu in a first terminal and keep it open:

```bash
cd /home/suresh/project/dynamic-firewall
bash scripts/run_controller.sh
```

Confirm listeners on TCP 6653 and 8080 with `ss -ltnp | grep -E ':6653|:8080'`. In a second terminal, with root privileges, run the complete test:

```bash
cd /home/suresh/project/dynamic-firewall
sudo /usr/bin/python3 tests/run_integration.py
```

Mininet comes from Ubuntu's system Python, so use `/usr/bin/python3` for this runner. The runner creates s1 and h1/h2/h3, requires the switch to connect, verifies OpenFlow 1.3, checks baseline ping and zero packet loss **before** issuing a block, verifies both OVS drop rules and blocked/unaffected traffic, removes the policy, and verifies recovery. It writes actual results to `reports/integration-results.json` and raw terminal evidence to `screenshots/terminal-evidence/`. It always stops the Mininet network in a `finally` block.

To reproduce the twelve screenshots of saved evidence after a successful run, install Ubuntu's `python3-pil`, `xvfb`, and `xterm` packages if needed, then run `/usr/bin/python3 scripts/capture_evidence_images.py`. These are real captures of a virtual terminal displaying the raw output; they are not live Mininet screenshots.

For a manual Mininet CLI session:

```bash
sudo mn --custom topology.py --topo firewalltopo \
  --switch ovsk,protocols=OpenFlow13 \
  --controller remote,ip=127.0.0.1,port=6653
```

At `mininet>`, run `nodes`, `net`, and `pingall`. Stop if baseline connectivity fails. In another terminal, run:

```bash
curl -s http://127.0.0.1:8080/firewall/blocked
curl -s -X POST http://127.0.0.1:8080/firewall/block/10.0.0.2
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

At `mininet>`, run `h1 ping -c 3 h2`, `h3 ping -c 3 h2`, and `h1 ping -c 3 h3`. The first two should have 100% loss; the last should have 0% loss. Then:

```bash
curl -s -X POST http://127.0.0.1:8080/firewall/unblock/10.0.0.2
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

Run `h1 ping -c 3 h2`, `h3 ping -c 3 h2`, and `pingall` again. All should have 0% loss under normal lab conditions. Exit Mininet with `exit`. If a prior run left stale Mininet interfaces, use `sudo mn -c` before retrying.

`tests/check_api_without_switch.py` tests the REST service when no switch is connected. It intentionally expects a 503 for a valid block request; that check says nothing about packet enforcement.
