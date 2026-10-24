# Validation report — 2026-10-24 UTC

The root-enabled integration run completed with `PASS`. It created the three-host OpenFlow 1.3 topology, verified baseline ping **before** blocking, installed and inspected two actual OVS drop rules, observed selective packet loss, removed the rules, and verified recovery. The machine used Python 3.11.17, Ryu 4.34, Eventlet 0.41.3, Mininet 2.3.0, and OVS 3.7.1. The full machine-readable result is [`integration-results.json`](../dynamic-firewall/reports/integration-results.json).

## Required results

| Test | Action | Expected result | Actual result | Status | Supporting evidence | Observation |
|---:|---|---|---|---|---|---|
| 1 | Start controller | Controller on 6653 | Ryu loaded app; TCP 6653 and HTTP 8080 listening | **PASS** | [startup](../dynamic-firewall/screenshots/terminal-evidence/01_controller_startup.txt), [listeners](../dynamic-firewall/screenshots/terminal-evidence/01_listeners.txt) | Eventlet warnings did not prevent startup |
| 2 | Start Mininet | h1/h2/h3, s1 connected over OF1.3 | Three hosts, one switch, three links, `[OpenFlow13]`; switch connected | **PASS** | [topology](../dynamic-firewall/screenshots/terminal-evidence/02_topology.json) | DPID 1 accepted by Ryu |
| 3 | Ping before blocking | 0% loss | h1→h2, h1→h3, h2→h3, h3→h1 each 0%; `pingAll` 0% | **PASS** | [baseline h1→h2](../dynamic-firewall/screenshots/terminal-evidence/03_baseline_h1h2.txt), [all hosts](../dynamic-firewall/screenshots/terminal-evidence/03_baseline_all_hosts.txt) | Baseline gate passed before block |
| 4 | Check blocked list | Empty | HTTP 200, `blocked_ips: []`, switch connected | **PASS** | [initial list](../dynamic-firewall/screenshots/terminal-evidence/04_initial_blocked.json) | No policy active |
| 5 | Block Client 2 | Drop flows installed | HTTP 200, `blocked: true`; list contains `10.0.0.2` | **PASS** | [block response](../dynamic-firewall/screenshots/terminal-evidence/05_block_response.json), [blocked list](../dynamic-firewall/screenshots/terminal-evidence/05_blocked_list.json) | Flow table checked separately in Test 8 |
| 6 | Ping Client 2 | h1→h2 and h3→h2 fail | Both 100% loss; h2→h1 also 100% loss | **PASS** | [h1→h2](../dynamic-firewall/screenshots/terminal-evidence/06_during_h1h2.txt), [h3→h2](../dynamic-firewall/screenshots/terminal-evidence/06_during_h3h2.txt), [h2→h1](../dynamic-firewall/screenshots/terminal-evidence/06_during_h2h1.txt) | Both source and destination rule paths exercised |
| 7 | Ping Client 3 | h1→h3 succeeds | 0% loss | **PASS** | [unaffected ping](../dynamic-firewall/screenshots/terminal-evidence/06_during_h1h3.txt) | Selective blocking observed |
| 8 | Inspect flow table | Priority-100 drop for 10.0.0.2 | Two priority-100 `ip` rules with `nw_src` and `nw_dst`, both `actions=drop`; priority-0 `NORMAL` remains | **PASS** | [OVS flows during block](../dynamic-firewall/screenshots/terminal-evidence/07_flows_during.txt) | Dump was taken immediately after installation, before blocked pings |
| 9 | Unblock Client 2 | Drop flows removed | HTTP 200, `blocked: false`; list empty; no priority-100 drops | **PASS** | [unblock response](../dynamic-firewall/screenshots/terminal-evidence/08_unblock_response.json), [list](../dynamic-firewall/screenshots/terminal-evidence/08_unblocked_list.json), [flows after](../dynamic-firewall/screenshots/terminal-evidence/08_flows_after.txt) | No network restart |
| 10 | Ping Client 2 again | Connectivity restored | h1→h2, h3→h2, h2→h1 each 0% loss | **PASS** | [h1→h2 recovery](../dynamic-firewall/screenshots/terminal-evidence/09_recovery_h1h2.txt), [h3→h2 recovery](../dynamic-firewall/screenshots/terminal-evidence/09_recovery_h3h2.txt) | Communication returned |
| 11 | Run all-host test | 0% loss | `pingAll` 0% | **PASS** | [recovery all hosts](../dynamic-firewall/screenshots/terminal-evidence/09_recovery_all_hosts.txt) | Same as baseline |

The [six unit tests](../dynamic-firewall/screenshots/terminal-evidence/10_unit_tests.txt) passed. They cover client validation, source/destination drop construction, exact deletion, disconnected-switch rejection, barrier-gated state, and reconnect replay. The [six disconnected-switch REST checks](../dynamic-firewall/reports/api-without-switch.json) also passed, including correct HTTP 503 behavior when s1 is absent. With s1 connected, a [duplicate block](../dynamic-firewall/screenshots/terminal-evidence/05_duplicate_block.json) returned 409 and a [repeated unblock](../dynamic-firewall/screenshots/terminal-evidence/08_repeated_unblock.json) returned 404.

## Measurements from this run

| Measurement | Before | During block | After unblock |
|---|---:|---:|---:|
| All-host ping packet loss | 0% | Selective: h1→h2, h3→h2, h2→h1 100%; h1→h3 0% | 0% |
| Priority-100 drop flow count | 0 | 2 | 0 |
| Request start → confirmed OVS rule state | — | 0.0285 s | 0.0240 s for removal |

Timing includes the HTTP request and an `ovs-ofctl` verification poll; it is a single local lab measurement, not a latency guarantee. The [before](../dynamic-firewall/screenshots/terminal-evidence/03_flows_before.txt), [during](../dynamic-firewall/screenshots/terminal-evidence/07_flows_during.txt), and [after](../dynamic-firewall/screenshots/terminal-evidence/08_flows_after.txt) switch dumps show the rule count change.

## Screenshots and raw evidence

The test runner saved genuine command output and machine-readable evidence for every required phase in [`screenshots/terminal-evidence`](../dynamic-firewall/screenshots/terminal-evidence). Twelve [PNG screenshots](../dynamic-firewall/screenshots) show that saved output in an Xvfb terminal. They were captured **after** the run from the raw evidence files, so they document the observed output rather than a live Mininet window. The desktop screenshot API denied direct capture; the virtual terminal method produced real window screenshots without changing the test data.

| Requested view | Image |
|---|---|
| Ryu controller | [01_controller_running.png](../dynamic-firewall/screenshots/01_controller_running.png) |
| Topology | [02_topology.png](../dynamic-firewall/screenshots/02_topology.png) |
| Baseline connectivity | [03_baseline_connectivity.png](../dynamic-firewall/screenshots/03_baseline_connectivity.png) |
| Block response | [04_block_response.png](../dynamic-firewall/screenshots/04_block_response.png) |
| Blocked list | [05_blocked_list.png](../dynamic-firewall/screenshots/05_blocked_list.png) |
| Blocked pings | [06_blocked_pings.png](../dynamic-firewall/screenshots/06_blocked_pings.png) |
| Unaffected ping | [07_unaffected_ping.png](../dynamic-firewall/screenshots/07_unaffected_ping.png) |
| OVS drop rules | [08_ovs_drop_rules.png](../dynamic-firewall/screenshots/08_ovs_drop_rules.png) |
| Unblock response | [09_unblock_response.png](../dynamic-firewall/screenshots/09_unblock_response.png) |
| OVS rules removed | [10_ovs_rules_removed.png](../dynamic-firewall/screenshots/10_ovs_rules_removed.png) |
| Recovered ping | [11_recovered_ping.png](../dynamic-firewall/screenshots/11_recovered_ping.png) |
| Final all-host ping | [12_final_all_hosts.png](../dynamic-firewall/screenshots/12_final_all_hosts.png) |
