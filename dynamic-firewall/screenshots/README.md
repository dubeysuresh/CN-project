# Evidence directory

`terminal-evidence/` holds captured text and JSON from commands actually executed in this workspace, including the root-enabled Mininet/OVS integration run. The test measurements are in `../reports/integration-results.json`.

The twelve PNG files are actual screenshots of an Xvfb terminal displaying the saved evidence files. They were captured after the run because the desktop screenshot service rejected direct capture. The PNGs do not claim to show a live Mininet CLI. Reproduce them with `/usr/bin/python3 scripts/capture_evidence_images.py` after running the integration test; it requires Ubuntu's Pillow, Xvfb, and xterm packages.
