import urllib.request
import time
import random
import sys

BASE_URL = "http://localhost:8001"
ENDPOINTS = [
    ("/api/workload/fast", 0.70),
    ("/api/workload/slow", 0.20),
    ("/api/workload/error", 0.10),
]

print("[Traffic Simulator] Starting continuous background traffic pump...")

count = 0
while True:
    try:
        r = random.random()
        chosen_path = "/api/workload/fast"
        cum = 0
        for path, weight in ENDPOINTS:
            cum += weight
            if r <= cum:
                chosen_path = path
                break

        url = f"{BASE_URL}{chosen_path}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                code = resp.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception:
            code = "ERR"

        count += 1
        if count % 10 == 0:
            print(f"[Simulated {count} requests] Last: {chosen_path} -> {code}")
            sys.stdout.flush()

        time.sleep(random.uniform(0.3, 0.7))
    except KeyboardInterrupt:
        break
    except Exception as e:
        time.sleep(1)
