# Troubleshooting, decisions, and limits

## Issues encountered

| Issue | Cause | Resolution or status |
|---|---|---|
| Ryu wheel build failed with `easy_install.get_script_args` | Ryu 4.34 expects an API removed by newer setuptools | Pin `setuptools==58.0.4` and install with `--no-build-isolation`; `scripts/bootstrap.sh` reproduces this |
| Ryu startup failed with `ALREADY_HANDLED` import | PyPI Ryu 4.34 predates a newer Eventlet API | Bootstrap applies the upstream-style `getattr(eventlet.wsgi, 'ALREADY_HANDLED', None)` compatibility change inside `.venv` |
| Older Eventlet 0.30.2 failed on Python 3.11 | It attempts to modify immutable `TimeoutError` | Use Eventlet 0.41.3 and dnspython 2.9.0 with the Ryu compatibility patch |
| First Mininet attempt could not start | Mininet requires root; `sudo -n` required authentication | Root authorization was supplied later; the full integration run passed |
| Eventlet warning at startup | Eventlet itself reports deprecation; Ryu also reports one RLock not greened | Controller and REST service still started and responded; no network claim follows from this |

## Design decisions

The API only accepts three configured host addresses. This prevents a typo from installing a policy for an unrelated address. The block policy uses **two** rules so traffic both from and to the blocked IPv4 client is dropped. The reference source-only rule would not stop an inbound echo request by itself.

OVS `NORMAL` supplies ordinary L2 forwarding. This keeps the baseline simple and avoids per-packet controller latency for allowed traffic. OpenFlow priority 100 makes the firewall decision override the priority-0 default. Exact-match deletion and unique cookies avoid removing unrelated switch rules. Cookie-based cleanup reconciles stale firewall rules after a controller restart; the blocked policy set is replayed after a switch reconnect.

REST success waits for a barrier reply. A barrier confirms that the switch processed earlier OpenFlow messages, while `ovs-ofctl` and packet tests verify actual enforcement. The integration runner refuses to proceed to blocking if baseline connectivity is not correct.

## Limits and operational checks

- Only IPv4 source and destination are filtered. ARP, IPv6, and other EtherTypes are not blocked. A blocked host may still answer ARP.
- The switch uses `NORMAL`, an OVS extension behavior for L2 forwarding; the firewall rules themselves are OpenFlow 1.3.
- The controller accepts only DPID 1. Another switch is logged as unexpected and not managed.
- IP addresses are not tied to switch ports or MAC identity. A host able to spoof its IP may evade this demonstration policy.
- The API is local-only and unauthenticated. Keep it bound to `127.0.0.1` for this lab.
- The blocked set lives in memory. A controller process restart clears desired policy and removes stale firewall flows on reconnect.
- On an OpenFlow error or timeout, partial application is possible. Inspect `ovs-ofctl -O OpenFlow13 dump-flows s1`; reconnecting s1 triggers a policy replay. A stronger production design would query flow stats, persist policy, and reconcile after every failure.
- Automatic suspicious-traffic detection was **not implemented**. Counting packet arrivals would not satisfy the requested new-TCP-connection-attempt semantics; the manual firewall and its network validation take priority.
- Ping failures alone would prove ICMP connectivity loss, not full TCP/UDP behavior. The OpenFlow match applies to all IPv4 protocols, but TCP/UDP packet tests are still desirable after the root-enabled run.

## If a root-enabled test fails

1. Check Ryu listener: `ss -ltnp | grep 6653` and `ss -ltnp | grep 8080`.
2. Check switch protocol and controller: `sudo ovs-vsctl get bridge s1 protocols` and `sudo ovs-vsctl get-controller s1`.
3. Check actual flows: `sudo ovs-ofctl -O OpenFlow13 dump-flows s1`. Confirm priority 0 `NORMAL` and, when blocked, two priority 100 drops.
4. Verify baseline ARP and ping before blocking: `mininet> h1 arp -n`, then `mininet> pingall`.
5. If the blocked list and switch table disagree, restart the controller and reconnect s1 to trigger cookie cleanup and policy replay; re-run the baseline before a new block test.
6. If connectivity does not recover, inspect for remaining priority 100 rules, then compare source/destination matches and cookies with the intended policy.
