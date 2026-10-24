"""Screenshot genuine saved test output displayed in an Xvfb terminal.

Run with Ubuntu's system Python (it provides Pillow). This does not alter test
results. The images are screenshots of recorded terminal evidence after the run.
"""

import pathlib
import subprocess
import time

from PIL import ImageGrab


ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "screenshots" / "terminal-evidence"
OUT = ROOT / "screenshots"
DISPLAY = ":100"
CAPTURES = [
    ("01_controller_running.png", "Ryu startup and controller log", ["01_controller_startup.txt"]),
    ("02_topology.png", "Mininet topology and OpenFlow version", ["02_topology.json"]),
    ("03_baseline_connectivity.png", "Baseline h1 to h2 and all-host ping", ["03_baseline_h1h2.txt", "03_baseline_all_hosts.txt"]),
    ("04_block_response.png", "Firewall block API response", ["05_block_response.json"]),
    ("05_blocked_list.png", "Blocked-client list", ["05_blocked_list.json"]),
    ("06_blocked_pings.png", "Blocked h1 to h2 and h3 to h2 pings", ["06_during_h1h2.txt", "06_during_h3h2.txt"]),
    ("07_unaffected_ping.png", "Unaffected h1 to h3 ping", ["06_during_h1h3.txt"]),
    ("08_ovs_drop_rules.png", "OVS OpenFlow 1.3 drop rules", ["07_flows_during.txt"]),
    ("09_unblock_response.png", "Firewall unblock API response", ["08_unblock_response.json"]),
    ("10_ovs_rules_removed.png", "OVS flow table after unblock", ["08_flows_after.txt"]),
    ("11_recovered_ping.png", "Recovered h1 to h2 ping", ["09_recovery_h1h2.txt"]),
    ("12_final_all_hosts.png", "Final all-host ping", ["09_recovery_all_hosts.txt"]),
]


def main():
    for _, _, files in CAPTURES:
        for name in files:
            if not (RAW / name).is_file():
                raise SystemExit(f"Missing actual test evidence: {name}")
    server = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1280x720x24", "-nolisten", "tcp"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.5)
        if server.poll() is not None:
            raise SystemExit("Virtual display failed to start")
        for filename, title, files in CAPTURES:
            command = ["xterm", "-display", DISPLAY, "-geometry", "140x36+12+12",
                       "-fa", "DejaVu Sans Mono", "-fs", "11",
                       "-bg", "#101820", "-fg", "#e5eef6", "-e", "sh", "-c",
                       "printf '%s\\n\\n' \"$1\"; shift; for file in \"$@\"; do cat \"$file\"; printf '\\n'; done; sleep 10",
                       "sh", title, *(str(RAW / name) for name in files)]
            terminal = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                time.sleep(1.5)
                if terminal.poll() is not None:
                    raise SystemExit(f"Terminal failed for {filename}")
                ImageGrab.grab(xdisplay=DISPLAY).save(OUT / filename)
                print(OUT / filename)
            finally:
                terminal.terminate()
                terminal.wait(timeout=3)
    finally:
        server.terminate()
        server.wait(timeout=3)


if __name__ == "__main__":
    main()
