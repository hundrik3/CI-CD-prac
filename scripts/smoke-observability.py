#!/usr/bin/env python3
"""Check actual HTTP behavior and exported metrics, traces, logs and alerts."""
import argparse
from datetime import datetime, timezone
import json
import re
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--app", default="http://127.0.0.1:8080")
parser.add_argument("--prometheus", default="http://127.0.0.1:9090")
parser.add_argument("--tempo", default="http://127.0.0.1:3200")
parser.add_argument("--loki", default="http://127.0.0.1:3100")
parser.add_argument("--grafana", default="http://127.0.0.1:3000")
parser.add_argument("--output", default=".local/observability-evidence.json")
args = parser.parse_args()
# This client is only for explicitly selected local lab endpoints.
client = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        response = client.open(req, timeout=5)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read()

def eventually(name, check, timeout=150):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            result = check()
            if result:
                print(name + ": PASS", flush=True)
                return result
        except (OSError, ValueError, KeyError) as error:
            last = str(error)
        time.sleep(2)
    raise RuntimeError(name + " timed out: " + str(last))

def query(expression):
    status, _, body = fetch(args.prometheus + "/api/v1/query?" + urllib.parse.urlencode({"query": expression}))
    if status != 200:
        return []
    return json.loads(body)["data"]["result"]

eventually("app health", lambda: fetch(args.app + "/healthz")[0] == 200)
assert json.loads(fetch(args.app + "/")[2])["service"] == "portfolio-api"
assert fetch(args.app + "/work?delay_ms=-1")[0] == 400
assert fetch(args.app + "/error")[0] == 500
# Establish a scraped baseline before exercising an increase-based alert.
raw_metrics = fetch(args.app + "/metrics")[2].decode()
baseline = float(re.search(r'portfolio_requests_total\{route="/error",status="500"\} ([0-9.e+]+)', raw_metrics).group(1))
def counter_value():
    samples = query('sum(portfolio_requests_total{status="500"})')
    return float(samples[0]['value'][1]) if samples else None
eventually("fresh error metric baseline", lambda: counter_value() == baseline)
started = time.monotonic()
status, headers, body = fetch(args.app + "/work?delay_ms=150")
assert status == 200 and json.loads(body)["delay_ms"] == 150
assert time.monotonic() - started >= 0.14
trace_id = headers.get("X-Trace-ID")
assert trace_id and len(trace_id) == 32 and int(trace_id, 16) != 0
for _ in range(5):
    assert fetch(args.app + "/error")[0] == 500
eventually("request metrics", lambda: counter_value() is not None and counter_value() >= baseline + 5)
metrics = query('sum(portfolio_requests_total{status="500"})')
eventually("trace lookup", lambda: fetch(args.tempo + "/api/traces/" + trace_id)[0] == 200)
logs_url = args.loki + "/loki/api/v1/query_range?" + urllib.parse.urlencode({"query": '{service_name="portfolio-api"}', "limit": 100})
eventually("correlated logs", lambda: trace_id in fetch(logs_url)[2].decode())
eventually("firing error alert", lambda: any(a['labels']['alertname'] == 'PortfolioErrors' and a['state'] == 'firing' for a in json.loads(fetch(args.prometheus + '/api/v1/alerts')[2])['data']['alerts']))
eventually("provisioned Grafana dashboard", lambda: fetch(args.grafana + "/api/dashboards/uid/portfolio-api")[0] == 200)
result = {"checked_at": datetime.now(timezone.utc).isoformat(), "app": args.app, "trace_id": trace_id, "error_metric": metrics, "checks": ["health", "bounded input", "150ms work", "HTTP 500", "metrics", "Tempo trace", "Loki correlated log", "Prometheus firing alert", "Grafana dashboard"]}
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
print("All functional observability checks passed.", flush=True)
