# Dynamic Firewall documentation

Open [index.html](index.html) for the designed, navigable HTML report. It explains what the project does, how Ryu and OVS enforce the policy, why the design uses two IPv4 drop rules, and what the completed Mininet test actually verified.

## HTML hierarchy

| Location | Content |
|---|---|
| [index.html](index.html) | Top-level overview and measured outcomes |
| [pages/topology.html](pages/topology.html) | Topology, component roles, ARP and IPv4 paths, interactive traffic states |
| [pages/firewall.html](pages/firewall.html) | OpenFlow matches, priority, REST contract, barriers, design choices |
| [pages/testing.html](pages/testing.html) | Eleven PASS results, packet loss matrix, flow and timing charts |
| [pages/evidence.html](pages/evidence.html) | Twelve screenshot gallery and raw evidence links |
| [pages/guide.html](pages/guide.html) | Setup, commands, troubleshooting, limits |
| `assets/` | Shared CSS/JS and evidence copied from the sibling project |

The HTML files are generated from `content/` fragments with a shared shell in `build_site.py`. Run `python3 build_site.py` from this directory after editing a fragment or after rerunning the network test. The build also refreshes evidence copies from `../dynamic-firewall` when that project is present.

The original Markdown notes remain available: [topology and architecture](topology-and-architecture.md), [policy and theory](policy-and-theory.md), [runbook](runbook.md), [validation report](validation-report.md), and [troubleshooting and limits](troubleshooting-and-limits.md).

The root-enabled Mininet/OVS integration run passed all eleven required phases. The PNG evidence is a screenshot of genuine saved terminal output taken after the run, and the raw files remain available in the [evidence archive](pages/evidence.html).
