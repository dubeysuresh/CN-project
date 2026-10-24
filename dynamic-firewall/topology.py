"""Three-host, one-switch Mininet topology for the dynamic firewall."""

from mininet.topo import Topo


class FirewallTopo(Topo):
    def build(self):
        switch = self.addSwitch("s1", dpid="0000000000000001", protocols="OpenFlow13")
        for number in (1, 2, 3):
            host = self.addHost(f"h{number}", ip=f"10.0.0.{number}/24")
            self.addLink(host, switch)


topos = {"firewalltopo": FirewallTopo}
