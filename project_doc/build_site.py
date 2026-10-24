"""Build the standalone HTML report from shared navigation and page fragments."""

from html import escape
from pathlib import Path
from shutil import copy2


ROOT = Path(__file__).resolve().parent
NAV = [
    ("overview", "Overview", "◈", "index.html"),
    ("topology", "Topology & architecture", "⌘", "pages/topology.html"),
    ("firewall", "Firewall logic", "◇", "pages/firewall.html"),
    ("testing", "Validation & results", "▥", "pages/testing.html"),
    ("evidence", "Evidence gallery", "▦", "pages/evidence.html"),
    ("guide", "Runbook & limits", "↗", "pages/guide.html"),
]
PAGES = [
    ("overview", "Overview", "A verified SDN security lab", "content/home.html", "index.html", "topology"),
    ("topology", "Topology & architecture", "One switch. Three hosts. One controller.", "content/topology.html", "pages/topology.html", "firewall"),
    ("firewall", "Firewall logic", "The policy becomes switch behavior.", "content/firewall.html", "pages/firewall.html", "testing"),
    ("testing", "Validation & results", "Real traffic, real flow rules.", "content/testing.html", "pages/testing.html", "evidence"),
    ("evidence", "Evidence gallery", "The observed output, preserved.", "content/evidence.html", "pages/evidence.html", "guide"),
    ("guide", "Runbook & limits", "Reproduce, inspect, understand.", "content/guide.html", "pages/guide.html", "overview"),
]
EVIDENCE = [
    ("01_controller_running.png", "Controller running", "Ryu loaded the firewall app and handled real switch and API events.", "01_controller_startup.txt", "control"),
    ("02_topology.png", "Three-host topology", "h1, h2, h3, s1, three links, and OpenFlow 1.3.", "02_topology.json", "network"),
    ("03_baseline_connectivity.png", "Baseline connectivity", "Before blocking, all-host ping had 0% loss.", "03_baseline_all_hosts.txt", "network"),
    ("04_block_response.png", "Block request accepted", "The API confirmed the block for 10.0.0.2.", "05_block_response.json", "control"),
    ("05_blocked_list.png", "Blocked list updated", "10.0.0.2 appeared in the controller policy list.", "05_blocked_list.json", "control"),
    ("06_blocked_pings.png", "h2 traffic denied", "h1→h2 and h3→h2 each showed 100% loss.", "06_during_h1h2.txt", "network"),
    ("07_unaffected_ping.png", "h1 and h3 unaffected", "Their ping stayed at 0% loss during the h2 block.", "06_during_h1h3.txt", "network"),
    ("08_ovs_drop_rules.png", "Drop rules on s1", "Two priority-100 IPv4 entries have actions=drop.", "07_flows_during.txt", "network"),
    ("09_unblock_response.png", "Unblock accepted", "The API confirmed removal of h2's restriction.", "08_unblock_response.json", "control recovery"),
    ("10_ovs_rules_removed.png", "Rules removed", "No priority-100 firewall entries remain on s1.", "08_flows_after.txt", "network recovery"),
    ("11_recovered_ping.png", "h2 connectivity restored", "h1→h2 returned to 0% packet loss.", "09_recovery_h1h2.txt", "recovery"),
    ("12_final_all_hosts.png", "Final all-host test", "All six directed pairs succeeded with 0% dropped.", "09_recovery_all_hosts.txt", "recovery"),
]


def gallery_markup():
    cards = []
    for number, (filename, title, description, raw, category) in enumerate(EVIDENCE, 1):
        cards.append(f'''<article class="evidence-card" data-category="{category}">
          <img class="evidence-img" src="{{{{ROOT}}}}assets/evidence/screenshots/{filename}" alt="Captured terminal evidence: {escape(title)}" loading="lazy">
          <div class="evidence-body"><span class="evidence-no">EVIDENCE / {number:02d}</span><h3>{escape(title)}</h3><p>{escape(description)}</p><div class="evidence-links"><a href="{{{{ROOT}}}}assets/evidence/raw/{raw}">Raw output ↗</a><button type="button" data-lightbox-src="{{{{ROOT}}}}assets/evidence/screenshots/{filename}" data-lightbox-title="{escape(title, quote=True)}">Expand ↗</button></div></div>
        </article>''')
    return "\n".join(cards)


def shell(key, title, description, content, target, next_key):
    prefix = "" if target == "index.html" else "../"
    nav = "\n".join(
        '<a class="nav-link" href="{}{}"{}><span class="nav-icon" aria-hidden="true">{}</span><span>{}</span></a>'.format(
            prefix, link, ' aria-current="page"' if nav_key == key else "", icon, escape(label)
        )
        for nav_key, label, icon, link in NAV
    )
    next_label = next(label for nav_key, label, _, _ in NAV if nav_key == next_key)
    next_link = next(link for nav_key, _, _, link in NAV if nav_key == next_key)
    content = content.replace("{{GALLERY}}", gallery_markup()).replace("{{ROOT}}", prefix)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="theme-color" content="#071116">
  <meta name="description" content="{escape(description, quote=True)}">
  <title>{escape(title)} · Dynamic Firewall</title>
  <link rel="stylesheet" href="{prefix}assets/site.css">
  <script src="{prefix}assets/site.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <div class="mobile-scrim" aria-hidden="true"></div>
  <div class="app-shell">
    <aside class="sidebar" aria-label="Site navigation">
      <a class="brand" href="{prefix}index.html" aria-label="Dynamic Firewall home">
        <span class="brand-mark"><svg viewBox="0 0 28 28" fill="none" aria-hidden="true"><path d="M14 4 23 9v10l-9 5-9-5V9l9-5Z" stroke="#70e4c5" stroke-width="1.6"/><circle cx="14" cy="9" r="2" fill="#70e4c5"/><circle cx="9" cy="17" r="2" fill="#70e4c5"/><circle cx="19" cy="17" r="2" fill="#70e4c5"/><path d="m14 11-4 5m5-5 3 5M11 17h6" stroke="#70e4c5" stroke-width="1.2"/></svg></span>
        <span><strong>Dynamic Firewall</strong><span>SDN controller · module 02</span></span>
      </a>
      <div class="nav-label">Explore the project</div>
      <nav class="site-nav" aria-label="Primary">{nav}</nav>
      <div class="side-foot"><div class="status-line"><span class="status-dot"></span> Verified on OVS</div><div>OpenFlow 1.3 · Ryu 4.34<br>Lab run: 24 Oct 2026</div></div>
    </aside>
    <main class="main" id="content">
      <div class="topbar"><div class="crumb">PROJECT <span class="sep">/</span> DYNAMIC FIREWALL <span class="sep">/</span> <b>{escape(title.upper())}</b></div><div class="topbar-right"><span class="top-tag">11 / 11 integration checks passed</span><button class="menu-button" type="button" data-menu-toggle aria-label="Open navigation" aria-expanded="false">☰</button></div></div>
      <div class="page-wrap">{content}
        <footer class="footer"><span>Dynamic Firewall / SDN Controller · Actual Mininet and OVS validation · 24 Oct 2026</span><a class="next-link" href="{prefix}{next_link}">Next: {escape(next_label)} <span aria-hidden="true">↗</span></a></footer>
      </div>
    </main>
  </div>
</body>
</html>
'''


def main():
    source = ROOT.parent / "dynamic-firewall"
    if source.exists():
        image_target = ROOT / "assets/evidence/screenshots"
        raw_target = ROOT / "assets/evidence/raw"
        image_target.mkdir(parents=True, exist_ok=True)
        raw_target.mkdir(parents=True, exist_ok=True)
        for path in (source / "screenshots").glob("*.png"):
            copy2(path, image_target / path.name)
        for path in (source / "screenshots/terminal-evidence").glob("*"):
            if path.is_file():
                copy2(path, raw_target / path.name)
        for name in ("integration-results.json", "api-without-switch.json"):
            path = source / "reports" / name
            if path.is_file():
                copy2(path, ROOT / "assets/evidence" / name)
    for key, title, description, fragment, target, next_key in PAGES:
        text = (ROOT / fragment).read_text()
        rendered = shell(key, title, description, text, target, next_key)
        output = ROOT / target
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered)
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
