"""Capture live REST behavior while s1 is disconnected; start Ryu first."""

import json
import pathlib
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = [
    ("GET", "/firewall/blocked", 200),
    ("POST", "/firewall/block/10.0.0.2", 503),
    ("POST", "/firewall/block/not-an-ip", 400),
    ("POST", "/firewall/block/10.0.1.1", 400),
    ("POST", "/firewall/block/10.0.0.4", 400),
    ("POST", "/firewall/unblock/10.0.0.2", 404),
]


def main():
    evidence = []
    for method, path, expected in CASES:
        request = urllib.request.Request("http://127.0.0.1:8080" + path, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status, body = response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            status, body = error.code, json.loads(error.read())
        item = {"method": method, "path": path, "status": status,
                "expected_status": expected, "body": body, "pass": status == expected}
        evidence.append(item)
        print(item)
    path = ROOT / "reports" / "api-without-switch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + "\n")
    if not all(item["pass"] for item in evidence):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
