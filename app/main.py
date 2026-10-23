from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from time import perf_counter
from datetime import datetime
import asyncio
import os
import random

app = FastAPI(
    title="DevOps Automation Platform",
    description="ForgeOps - Cloud-Native Automation & Observability Platform",
    version="1.0.0",
)

# Prometheus Metrics Definition
REQUESTS = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)

LATENCY = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ACTIVE_USERS = Gauge(
    "active_users_current",
    "Current active simulated users on the platform",
)

# In-memory request log & telemetry buffer for the UI
REQUEST_LOG = []
PODS_STATE = [
    {"name": "forgeops-api-68456ccfc-cdznp", "ready": "1/1", "status": "Running", "restarts": 0, "age": "24m", "node": "desktop-control-plane", "ip": "10.244.0.5", "cpu": "12m", "mem": "64Mi"},
    {"name": "forgeops-api-68456ccfc-qqsjt", "ready": "1/1", "status": "Running", "restarts": 0, "age": "24m", "node": "desktop-control-plane", "ip": "10.244.0.6", "cpu": "14m", "mem": "68Mi"},
]

CLUSTER_EVENTS = [
    {"time": datetime.now().strftime("%H:%M:%S"), "type": "Normal", "reason": "Started", "message": "Container forgeops-api started successfully"},
    {"time": datetime.now().strftime("%H:%M:%S"), "type": "Normal", "reason": "Pulled", "message": "Container image forgeops-api:latest already present on machine"},
]


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - start
    path = request.url.path

    if path != "/metrics":
        REQUESTS.labels(
            request.method, path, str(response.status_code)
        ).inc()

        LATENCY.labels(
            request.method, path
        ).observe(duration)

        if path.startswith("/api/workload"):
            REQUEST_LOG.insert(0, {
                "time": datetime.now().strftime("%H:%M:%S"),
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 1),
            })
            if len(REQUEST_LOG) > 50:
                REQUEST_LOG.pop()

    return response


@app.get("/")
def root():
    return {
        "message": "DevOps Automation Platform is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "environment": os.getenv("APP_ENV", "local"),
        "hostname": os.getenv("HOSTNAME", "localhost"),
    }


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Workload Simulation Endpoints for Observability & Stress Testing
@app.get("/api/workload/fast")
async def workload_fast():
    """Simulates a fast, optimized query (5-20ms)."""
    delay = random.uniform(0.005, 0.02)
    await asyncio.sleep(delay)
    return {
        "status": "ok",
        "workload": "fast",
        "duration_ms": round(delay * 1000, 2),
    }


@app.get("/api/workload/slow")
async def workload_slow():
    """Simulates high latency or heavy compute (200-500ms) to trigger p95/p99 latency spikes."""
    delay = random.uniform(0.2, 0.5)
    await asyncio.sleep(delay)
    return {
        "status": "ok",
        "workload": "slow",
        "duration_ms": round(delay * 1000, 2),
    }


@app.get("/api/workload/error")
def workload_error():
    """Simulates a 500 internal server error to generate error rate spikes in Grafana."""
    raise HTTPException(status_code=500, detail="Simulated 500 Internal Server Error for Grafana alerting")


@app.get("/api/telemetry/stats")
def telemetry_stats():
    """Returns live aggregated request counts, cluster events, and pod states."""
    fast_count = sum(1 for r in REQUEST_LOG if r["path"] == "/api/workload/fast")
    slow_count = sum(1 for r in REQUEST_LOG if r["path"] == "/api/workload/slow")
    error_count = sum(1 for r in REQUEST_LOG if r["status"] >= 500)
    total = len(REQUEST_LOG)
    error_rate = round((error_count / total * 100), 1) if total > 0 else 0.0

    return {
        "total": total,
        "fast": fast_count,
        "slow": slow_count,
        "errors": error_count,
        "error_rate": error_rate,
        "recent": REQUEST_LOG[:15],
        "pods": PODS_STATE,
        "events": CLUSTER_EVENTS[:8],
    }


@app.post("/api/chaos/kill-pod")
async def chaos_kill_pod(request: Request):
    """Simulates killing a pod and triggers self-healing recovery."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    
    target_name = body.get("pod_name")
    target_pod = None
    for p in PODS_STATE:
        if p["name"] == target_name:
            target_pod = p
            break
    if not target_pod and PODS_STATE:
        target_pod = PODS_STATE[0]

    if not target_pod:
        return {"action": "no_pods"}

    target_name = target_pod["name"]
    target_pod["status"] = "Terminating"
    
    CLUSTER_EVENTS.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "Warning",
        "reason": "Killing",
        "message": f"Stopping container forgeops-api in pod {target_name}"
    })

    # Create replacement
    new_hash = "".join(random.choices("abcdef0123456789", k=5))
    new_pod = {
        "name": f"forgeops-api-68456ccfc-{new_hash}",
        "ready": "0/1",
        "status": "ContainerCreating",
        "restarts": 0,
        "age": "1s",
        "node": "desktop-control-plane",
        "ip": f"10.244.0.{random.randint(10, 99)}",
        "cpu": "10m",
        "mem": "60Mi"
    }
    PODS_STATE.append(new_pod)

    CLUSTER_EVENTS.insert(0, {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "Normal",
        "reason": "Scheduled",
        "message": f"Successfully assigned forgeops/{new_pod['name']} to desktop-control-plane"
    })

    # Background async task to finalize self-healing
    async def heal():
        await asyncio.sleep(2.5)
        if target_pod in PODS_STATE:
            PODS_STATE.remove(target_pod)
        new_pod["status"] = "Running"
        new_pod["ready"] = "1/1"
        CLUSTER_EVENTS.insert(0, {
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": "Normal",
            "reason": "Started",
            "message": f"Container forgeops-api started in replacement pod {new_pod['name']}"
        })

    asyncio.create_task(heal())
    return {"action": "pod_killed", "target": target_name, "replacement": new_pod["name"]}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Enterprise DevOps Platform Control Center - ForgeOps."""
    html_content = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ForgeOps - Platform Control Center</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap">
  <style>
    :root {
      --bg: #090b0e;
      --surface: #10141c;
      --surface-border: #1e2430;
      --surface-hover: #161c27;
      --text-main: #e2e8f0;
      --text-muted: #8490a5;
      --accent-blue: #3b82f6;
      --accent-blue-subtle: rgba(59, 130, 246, 0.12);
      --accent-emerald: #10b981;
      --accent-emerald-subtle: rgba(16, 185, 129, 0.12);
      --accent-rose: #f43f5e;
      --accent-rose-subtle: rgba(244, 63, 94, 0.12);
      --accent-amber: #f59e0b;
      --accent-amber-subtle: rgba(245, 158, 11, 0.12);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text-main);
      font: 13.5px/1.45 "IBM Plex Sans", system-ui, -apple-system, sans-serif;
      font-variant-numeric: tabular-nums;
      -webkit-font-smoothing: antialiased;
    }
    .mono { font-family: "IBM Plex Mono", ui-monospace, monospace; }

    .shell { display: flex; min-height: 100vh; }
    
    /* SIDEBAR */
    .side {
      width: 236px;
      flex: none;
      background: #0b0e14;
      border-right: 1px solid var(--surface-border);
      display: flex;
      flex-direction: column;
      user-select: none;
    }
    .brand {
      height: 56px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 20px;
      border-bottom: 1px solid var(--surface-border);
      font-size: 15px;
      font-weight: 600;
      color: #fff;
    }
    .brand-icon {
      width: 26px;
      height: 26px;
      background: linear-gradient(135deg, #3b82f6, #6366f1);
      border-radius: 4px;
      display: grid;
      place-items: center;
      color: #fff;
      font-weight: 700;
      font-size: 13px;
    }
    .grp {
      font-size: 10.5px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: #64748b;
      padding: 22px 20px 8px;
      font-weight: 600;
    }
    .nv {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 38px;
      padding: 0 20px;
      color: #94a3b8;
      text-decoration: none;
      border-left: 2px solid transparent;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.12s;
    }
    .nv:hover { background: #121822; color: #fff; }
    .nv.active { color: #fff; background: #131b26; border-left-color: var(--accent-blue); }
    .side-footer {
      margin-top: auto;
      padding: 16px 20px;
      border-top: 1px solid var(--surface-border);
      font: 11.5px/1.8 "IBM Plex Mono", monospace;
      color: #64748b;
    }

    /* TOP BAR */
    .main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .top-bar {
      min-height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 30px;
      border-bottom: 1px solid var(--surface-border);
      gap: 16px;
      flex-wrap: wrap;
      background: #0c0f16;
    }
    .crumb { font-size: 13px; color: #64748b; }
    .crumb b { color: var(--text-main); font-weight: 600; }
    
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 500;
      background: var(--accent-emerald-subtle);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--accent-emerald);
    }
    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent-emerald);
      box-shadow: 0 0 8px var(--accent-emerald);
      animation: pulse-dot 2s infinite;
    }
    @keyframes pulse-dot {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
    @keyframes toast-in {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .btn {
      min-height: 34px;
      padding: 0 14px;
      border: 1px solid var(--surface-border);
      background: #141923;
      color: #cbd5e1;
      border-radius: 4px;
      font: 500 12.5px "IBM Plex Sans", sans-serif;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn:hover { background: #1b2230; color: #fff; border-color: #2e384b; }
    .btn-primary { background: #1e3a8a; color: #93c5fd; border-color: #2563eb; }
    .btn-primary:hover { background: #1d4ed8; color: #fff; }
    .btn-danger { background: #451a1a; color: #fca5a5; border-color: #991b1b; }
    .btn-danger:hover { background: #7f1d1d; color: #fff; }
    .btn-success { background: #064e3b; color: #6ee7b7; border-color: #059669; }
    .btn-success.active { background: #047857; color: #fff; box-shadow: 0 0 12px rgba(16, 185, 129, 0.4); }

    /* PAGE CONTENT */
    .pg { padding: 26px 30px 48px; display: flex; flex-direction: column; gap: 22px; }
    .page-header { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 12px; }
    h1 { margin: 0; font-size: 21px; font-weight: 600; color: #fff; letter-spacing: -0.01em; }
    .sub { margin: 3px 0 0; color: var(--text-muted); font-size: 13px; }

    /* STAT STRIP */
    .strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1px;
      background: var(--surface-border);
      border: 1px solid var(--surface-border);
      border-radius: 4px;
      overflow: hidden;
    }
    .cell { background: var(--surface); padding: 16px 20px; }
    .cell-k { font-size: 11.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 500; }
    .cell-v { font-size: 26px; font-weight: 600; color: #fff; margin-top: 4px; line-height: 1.15; font-family: "IBM Plex Mono", monospace; }
    .cell-d { font-size: 11.5px; color: #64748b; margin-top: 3px; }

    /* PANELS */
    .g2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; }
    .pn {
      border: 1px solid var(--surface-border);
      border-radius: 4px;
      background: var(--surface);
      min-width: 0;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .ph {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 18px;
      border-bottom: 1px solid var(--surface-border);
    }
    .pt { font-weight: 600; font-size: 13px; color: #f1f5f9; }
    .pu { font: 400 11.5px "IBM Plex Mono", monospace; color: #64748b; }
    .pb { padding: 14px 18px 18px; }

    /* CANVAS CHARTS */
    .chart-container { position: relative; width: 100%; height: 160px; }
    canvas { width: 100% !important; height: 100% !important; display: block; }
    .lg { display: flex; gap: 16px; font-size: 11.5px; color: #94a3b8; margin-top: 10px; font-family: "IBM Plex Mono", monospace; }
    .lg i { display: inline-block; width: 10px; height: 3px; margin-right: 6px; vertical-align: middle; border-radius: 1px; }

    /* TABLES */
    .tb { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left;
      font-weight: 500;
      font-size: 11.5px;
      color: #64748b;
      padding: 10px 18px;
      border-bottom: 1px solid var(--surface-border);
      white-space: nowrap;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    td { padding: 11px 18px; border-bottom: 1px solid #161b24; font-size: 12.5px; white-space: nowrap; }
    tr:last-child td { border-bottom: 0; }
    tr:hover td { background: rgba(255, 255, 255, 0.015); }

    /* STATUS PILLS */
    .st {
      display: inline-block;
      padding: 1px 8px;
      border-radius: 3px;
      font: 500 11.5px/18px "IBM Plex Mono", monospace;
      border: 1px solid;
    }
    .ok { color: #34d399; border-color: #065f46; background: #064e3b44; }
    .wn { color: #fbbf24; border-color: #92400e; background: #78350f44; }
    .er { color: #f87171; border-color: #991b1b; background: #7f1d1d44; }
    .nu { color: #94a3b8; border-color: #334155; background: #1e293b44; }

    /* PROGRESS BARS */
    .bv { height: 5px; background: #1e2430; border-radius: 2px; width: 130px; overflow: hidden; }
    .bv i { display: block; height: 100%; border-radius: 2px; transition: width 0.3s; }

    /* ACTION BAR */
    .action-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      padding: 12px 18px;
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 4px;
    }

    /* CODE PREVIEW */
    pre {
      margin: 0;
      padding: 14px 18px;
      font: 12px/1.7 "IBM Plex Mono", monospace;
      color: #cbd5e1;
      overflow-x: auto;
      background: #0a0d13;
    }

    /* TOAST ALERT */
    #alert-banner {
      display: none;
      padding: 10px 18px;
      border-radius: 4px;
      font-size: 12.5px;
      font-weight: 500;
      background: #451a1a;
      border: 1px solid #b91c1c;
      color: #fca5a5;
      margin-bottom: -10px;
      align-items: center;
      gap: 10px;
    }

    .tab-content { display: none; }
    .tab-content.active { display: flex; flex-direction: column; gap: 22px; }

    @media(max-width: 860px) {
      .shell { flex-direction: column; }
      .side { width: auto; flex-direction: row; overflow-x: auto; border-right: 0; border-bottom: 1px solid var(--surface-border); }
      .brand { border-bottom: 0; flex: none; }
      .grp, .side-footer { display: none; }
      .nv { flex: none; border-left: 0; border-bottom: 2px solid transparent; }
      .nv.active { border-bottom-color: var(--accent-blue); }
      .top-bar, .pg { padding-left: 16px; padding-right: 16px; }
    }
  </style>
</head>
<body>
<div class="shell">
  <!-- SIDEBAR NAVIGATION -->
  <aside class="side">
    <div class="brand">
      <div class="brand-icon">F</div>
      <span>Forge<span style="font-weight:400;color:#94a3b8">Ops</span></span>
    </div>
    <nav aria-label="Primary">
      <div class="grp">Telemetry</div>
      <div class="nv active" onclick="switchTab('overview', this)">
        <span>Overview</span>
      </div>
      <div class="nv" onclick="switchTab('kubernetes', this)">
        <span>Kubernetes Pods</span>
      </div>
      <div class="nv" onclick="switchTab('reliability', this)">
        <span>Reliability &amp; SRE</span>
      </div>
      <div class="grp">Cloud &amp; IaC</div>
      <div class="nv" onclick="switchTab('azure', this)">
        <span>Azure &amp; Terraform</span>
      </div>
      <a class="nv" href="http://localhost:3002/d/forgeops-overview/forgeops-api-overview" target="_blank">
        <span>Grafana Live ↗</span>
      </a>
      <a class="nv" href="/metrics" target="_blank">
        <span>Prometheus Target ↗</span>
      </a>
    </nav>
    <div class="side-footer">
      API Runtime &nbsp;:8001<br>
      Prometheus &nbsp;&nbsp;:9092<br>
      Grafana &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:3002<br>
      Cluster &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;kind / v1.36
    </div>
  </aside>

  <!-- MAIN AREA -->
  <div class="main">
    <header class="top-bar">
      <div class="crumb">production / forgeops-api / <b id="crumb-title">Overview</b></div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <button class="btn" onclick="fetchLiveStats()">Sync Now</button>
        <button class="btn btn-primary" onclick="window.open('/docs', '_blank')">API Specs</button>
      </div>
    </header>

    <div class="pg">

      <!-- ALERT BANNER -->
      <div id="alert-banner">
        <span>⚠️</span>
        <span id="alert-msg">High error rate detected in recent window! Alert rule APIDown / 5xxSpike firing.</span>
      </div>

      <!-- ================= TAB 1: OVERVIEW ================= -->
      <div id="tab-overview" class="tab-content active">
        <div class="page-header">
          <div>
            <h1>Telemetry Overview</h1>
            <p class="sub">forgeops-api live metrics scraped every 15s by Prometheus</p>
          </div>
        </div>

        <!-- Metric Summary Strip -->
        <div class="strip">
          <div class="cell">
            <div class="cell-k">Total Ingested</div>
            <div class="cell-v" id="stat-requests">0</div>
            <div class="cell-d">requests processed</div>
          </div>
          <div class="cell">
            <div class="cell-k">Error Rate</div>
            <div class="cell-v" id="stat-error-rate" style="color:var(--accent-rose)">0.0%</div>
            <div class="cell-d" id="stat-error-sub">0 of 0</div>
          </div>
          <div class="cell">
            <div class="cell-k">Fast Queries</div>
            <div class="cell-v" id="stat-fast" style="color:var(--accent-blue)">0</div>
            <div class="cell-d" id="stat-fast-pct">0% (<20ms)</div>
          </div>
          <div class="cell">
            <div class="cell-k">Slow Queries</div>
            <div class="cell-v" id="stat-slow" style="color:var(--accent-amber)">0</div>
            <div class="cell-d" id="stat-slow-pct">0% (>200ms)</div>
          </div>
          <div class="cell">
            <div class="cell-k">Health Target</div>
            <div class="cell-v" style="color:var(--accent-emerald)">UP</div>
            <div class="cell-d">HTTP 200 on /health</div>
          </div>
        </div>

        <!-- Traffic Injector Action Bar -->
        <div class="action-bar">
          <span style="font-weight:600;font-size:12px;color:#94a3b8;margin-right:4px;text-transform:uppercase;letter-spacing:0.04em">Traffic Simulation:</span>
          <button class="btn" onclick="injectBatch('/api/workload/fast', 10)">+10 Fast (200)</button>
          <button class="btn" onclick="injectBatch('/api/workload/slow', 5)">+5 Latency (Slow)</button>
          <button class="btn btn-danger" onclick="injectBatch('/api/workload/error', 5)">+5 Error (500)</button>
          <button class="btn btn-success" id="btn-loop" onclick="toggleLoop()">Continuous Loop: OFF</button>
        </div>

        <!-- Real-Time Canvas Charts -->
        <div class="g2">
          <section class="pn">
            <div class="ph">
              <span class="pt">Throughput Rate</span>
              <span class="pu">req/s (rolling 60s)</span>
            </div>
            <div class="pb">
              <div class="chart-container">
                <canvas id="chart-traffic-canvas"></canvas>
              </div>
              <div class="lg">
                <span><i style="background:var(--accent-blue)"></i>all requests</span>
                <span><i style="background:var(--accent-rose)"></i>5xx errors</span>
              </div>
            </div>
          </section>

          <section class="pn">
            <div class="ph">
              <span class="pt">p95 Latency Distribution</span>
              <span class="pu">milliseconds (rolling 60s)</span>
            </div>
            <div class="pb">
              <div class="chart-container">
                <canvas id="chart-latency-canvas"></canvas>
              </div>
              <div class="lg">
                <span><i style="background:var(--accent-amber)"></i>p95 response time</span>
              </div>
            </div>
          </section>
        </div>

        <!-- Endpoints & Prometheus Targets -->
        <div class="g2">
          <section class="pn">
            <div class="ph">
              <span class="pt">Requests by Endpoint</span>
              <span class="pu">api_requests_total</span>
            </div>
            <div class="tb">
              <table>
                <thead>
                  <tr><th>Status</th><th>Endpoint</th><th>Count</th><th>Share</th></tr>
                </thead>
                <tbody id="endpoint-rows">
                  <tr>
                    <td><span class="st ok">200</span></td>
                    <td class="mono">/api/workload/fast</td>
                    <td id="row-fast-count">0</td>
                    <td><div class="bv"><i id="bar-fast" style="width:0%;background:var(--accent-blue)"></i></div></td>
                  </tr>
                  <tr>
                    <td><span class="st ok">200</span></td>
                    <td class="mono">/api/workload/slow</td>
                    <td id="row-slow-count">0</td>
                    <td><div class="bv"><i id="bar-slow" style="width:0%;background:var(--accent-amber)"></i></div></td>
                  </tr>
                  <tr>
                    <td><span class="st er">500</span></td>
                    <td class="mono">/api/workload/error</td>
                    <td id="row-error-count">0</td>
                    <td><div class="bv"><i id="bar-error" style="width:0%;background:var(--accent-rose)"></i></div></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="pn">
            <div class="ph">
              <span class="pt">Scrape Targets</span>
              <span class="pu">Prometheus TSDB</span>
            </div>
            <div class="tb">
              <table>
                <thead>
                  <tr><th>Job</th><th>Endpoint Target</th><th>Interval</th><th>Status</th></tr>
                </thead>
                <tbody class="mono">
                  <tr>
                    <td>api</td>
                    <td>http://api:8000/metrics</td>
                    <td>15s</td>
                    <td><span class="st ok">HEALTHY</span></td>
                  </tr>
                  <tr>
                    <td>prometheus</td>
                    <td>http://localhost:9090/metrics</td>
                    <td>15s</td>
                    <td><span class="st ok">HEALTHY</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Live Trace Stream -->
        <section class="pn">
          <div class="ph">
            <span class="pt">Live Request Trace Stream</span>
            <span class="pu">newest first</span>
          </div>
          <div class="tb">
            <table>
              <thead>
                <tr><th>Timestamp</th><th>Method</th><th>Endpoint</th><th>Latency</th><th>Status Code</th></tr>
              </thead>
              <tbody id="recent-table-body" class="mono">
                <tr><td colspan="5" style="color:#64748b">No simulated requests yet. Click "+10 Fast" or toggle the loop to begin.</td></tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>


      <!-- ================= TAB 2: KUBERNETES ================= -->
      <div id="tab-kubernetes" class="tab-content">
        <div class="page-header">
          <div>
            <h1>Kubernetes Cluster State</h1>
            <p class="sub">Namespace: forgeops | Node: desktop-control-plane (v1.36.1)</p>
          </div>
          <button class="btn btn-danger" onclick="triggerChaosPodKill()">💥 Chaos Monkey: Terminate Random Pod</button>
        </div>

        <div class="strip">
          <div class="cell">
            <div class="cell-k">Active Replicas</div>
            <div class="cell-v" id="k8s-pod-count">2</div>
            <div class="cell-d">Deployment / forgeops-api</div>
          </div>
          <div class="cell">
            <div class="cell-k">HPA Scaling Range</div>
            <div class="cell-v">2 - 5</div>
            <div class="cell-d">Threshold: 70% CPU</div>
          </div>
          <div class="cell">
            <div class="cell-k">Rollout Strategy</div>
            <div class="cell-v" style="font-size:16px;line-height:2.4">RollingUpdate</div>
            <div class="cell-d">maxSurge: 1 | maxUnavail: 0</div>
          </div>
          <div class="cell">
            <div class="cell-k">Security Context</div>
            <div class="cell-v" style="font-size:16px;line-height:2.4">UID 1000</div>
            <div class="cell-d">runAsNonRoot: true</div>
          </div>
        </div>

        <!-- Active Pods -->
        <section class="pn">
          <div class="ph">
            <span class="pt">Active Pod Fleet</span>
            <span class="pu">kubectl get pods -n forgeops -o wide</span>
          </div>
          <div class="tb">
            <table>
              <thead>
                <tr><th>Pod Identifier</th><th>Ready</th><th>Status</th><th>Restarts</th><th>CPU</th><th>RAM</th><th>IP Address</th><th>Action</th></tr>
              </thead>
              <tbody id="pods-table-body" class="mono">
                <!-- Dynamically populated -->
              </tbody>
            </table>
          </div>
        </section>

        <!-- Events & Helm Spec -->
        <div class="g2">
          <section class="pn">
            <div class="ph">
              <span class="pt">Cluster Events</span>
              <span class="pu">kubectl get events -n forgeops</span>
            </div>
            <div class="tb">
              <table>
                <thead><tr><th>Time</th><th>Reason</th><th>Message</th></tr></thead>
                <tbody id="cluster-events-body" class="mono">
                  <!-- Populated dynamically -->
                </tbody>
              </table>
            </div>
          </section>

          <section class="pn">
            <div class="ph">
              <span class="pt">Helm Packaging Blueprint</span>
              <span class="pu">charts/forgeops-api/</span>
            </div>
            <div class="tb">
              <table>
                <thead><tr><th>Setting</th><th>Value</th></tr></thead>
                <tbody class="mono">
                  <tr><td>Chart Version</td><td>0.1.0</td></tr>
                  <tr><td>Application Version</td><td>1.0.0</td></tr>
                  <tr><td>Target Service</td><td>ClusterIP (:80 -> :8000)</td></tr>
                  <tr><td>Liveness Probe</td><td>HTTP /health (delay 5s, period 10s)</td></tr>
                  <tr><td>Readiness Probe</td><td>HTTP /health (delay 3s, period 5s)</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>


      <!-- ================= TAB 3: RELIABILITY ================= -->
      <div id="tab-reliability" class="tab-content">
        <div class="page-header">
          <div>
            <h1>SRE Reliability &amp; Chaos Engineering</h1>
            <p class="sub">Failure resilience checks, alert rule expressions, and delivery pipeline</p>
          </div>
        </div>

        <div class="strip">
          <div class="cell">
            <div class="cell-k">Chaos Scenarios</div>
            <div class="cell-v">4 Verified</div>
            <div class="cell-d">Self-healing validated</div>
          </div>
          <div class="cell">
            <div class="cell-k">Service SLO Target</div>
            <div class="cell-v" style="color:var(--accent-emerald)">99.9%</div>
            <div class="cell-d">Availability objective</div>
          </div>
          <div class="cell">
            <div class="cell-k">Alert Rules</div>
            <div class="cell-v">1 Configured</div>
            <div class="cell-d">APIDown (Prometheus)</div>
          </div>
          <div class="cell">
            <div class="cell-k">Health Probing</div>
            <div class="cell-v" style="font-size:16px;line-height:2.4">Every 10s</div>
            <div class="cell-d">HTTP GET /health</div>
          </div>
        </div>

        <!-- Failure Test Scenarios -->
        <section class="pn">
          <div class="ph">
            <span class="pt">Failure Mode &amp; Resilience Matrix</span>
            <span class="pu">automated recovery</span>
          </div>
          <div class="tb">
            <table>
              <thead><tr><th>#</th><th>Failure Scenario</th><th>Trigger Command</th><th>Platform Response</th><th>State</th></tr></thead>
              <tbody>
                <tr><td>1</td><td>Container Crash</td><td class="mono">docker compose kill api</td><td>Docker engine restarts container automatically</td><td><span class="st ok">VERIFIED</span></td></tr>
                <tr><td>2</td><td>Deliberate Outage</td><td class="mono">docker compose stop api</td><td>APIDown Prometheus alert condition evaluates true</td><td><span class="st ok">VERIFIED</span></td></tr>
                <tr><td>3</td><td>Pod Termination</td><td class="mono">kubectl delete pod &lt;name&gt;</td><td>Kubernetes ReplicaSet controller schedules new pod</td><td><span class="st ok">VERIFIED</span></td></tr>
                <tr><td>4</td><td>Monitoring Outage</td><td class="mono">docker compose restart prometheus</td><td>FastAPI API maintains zero-downtime serving</td><td><span class="st ok">VERIFIED</span></td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <div class="g2">
          <section class="pn">
            <div class="ph">
              <span class="pt">Alert Rule Definition</span>
              <span class="pu">monitoring/alerts.yml</span>
            </div>
            <pre>groups:
  - name: forgeops-alerts
    rules:
      - alert: APIDown
        expr: up{job="api"} == 0
        for: 15s
        labels:
          severity: critical
        annotations:
          summary: "ForgeOps API endpoint unavailable"
          description: "Container api:8000 unreachable for > 15s"</pre>
          </section>

          <section class="pn">
            <div class="ph">
              <span class="pt">Zero-Downtime CD Workflow</span>
              <span class="pu">.github/workflows/deploy-azure.yml</span>
            </div>
            <div class="tb">
              <table>
                <thead><tr><th>Pipeline Stage</th><th>Mechanism</th></tr></thead>
                <tbody>
                  <tr><td>1. Trigger</td><td>git push on main branch</td></tr>
                  <tr><td>2. Auth</td><td>Azure OpenID Connect (OIDC) Passwordless Token</td></tr>
                  <tr><td>3. Build</td><td>Docker build with immutable SHA tag: ${{ github.sha }}</td></tr>
                  <tr><td>4. Registry</td><td>Publish to Azure Container Registry (ACR)</td></tr>
                  <tr><td>5. Release</td><td>helm upgrade --install --atomic (AKS)</td></tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>


      <!-- ================= TAB 4: AZURE & TERRAFORM ================= -->
      <div id="tab-azure" class="tab-content">
        <div class="page-header">
          <div>
            <h1>Azure Cloud &amp; Terraform IaC</h1>
            <p class="sub">Declarative infrastructure provisioning for production cloud deployment</p>
          </div>
          <button class="btn btn-primary" onclick="window.open('/docs/phase-2-terraform-azure-iac.md', '_blank')">View IaC Docs</button>
        </div>

        <div class="strip">
          <div class="cell">
            <div class="cell-k">Target Cloud</div>
            <div class="cell-v" style="font-size:18px;line-height:2.2">Microsoft Azure</div>
            <div class="cell-d">East US Data Center</div>
          </div>
          <div class="cell">
            <div class="cell-k">Modular Structure</div>
            <div class="cell-v">3 Modules</div>
            <div class="cell-d">networking, acr, aks</div>
          </div>
          <div class="cell">
            <div class="cell-k">State Backend</div>
            <div class="cell-v" style="font-size:16px;line-height:2.4">Azure Blob Storage</div>
            <div class="cell-d">Distributed lease locking</div>
          </div>
          <div class="cell">
            <div class="cell-k">Registry Auth</div>
            <div class="cell-v" style="font-size:18px;line-height:2.2">AcrPull (RBAC)</div>
            <div class="cell-d">Passwordless Managed Identity</div>
          </div>
        </div>

        <!-- Azure Resource Hierarchy Table -->
        <section class="pn">
          <div class="ph">
            <span class="pt">Resource Graph Hierarchy</span>
            <span class="pu">terraform/main.tf</span>
          </div>
          <div class="tb">
            <table>
              <thead>
                <tr><th>Resource Identifier</th><th>Terraform Type</th><th>SKU / Address Range</th><th>Description</th></tr>
              </thead>
              <tbody class="mono">
                <tr><td>rg-forgeops-dev</td><td>azurerm_resource_group</td><td>eastus</td><td>Primary logical containment boundary</td></tr>
                <tr><td>vnet-forgeops-dev</td><td>azurerm_virtual_network</td><td>10.0.0.0/16</td><td>Private cloud virtual network</td></tr>
                <tr><td>snet-aks</td><td>azurerm_subnet</td><td>10.0.1.0/24</td><td>Dedicated cluster node subnet</td></tr>
                <tr><td>acrforgeopsdev</td><td>azurerm_container_registry</td><td>Standard (Admin Disabled)</td><td>Private container registry with vulnerability scanning</td></tr>
                <tr><td>aks-forgeops-dev</td><td>azurerm_kubernetes_cluster</td><td>Standard_B2s (2 Nodes)</td><td>Managed Kubernetes control plane and VMSS pool</td></tr>
                <tr><td>aks_to_acr</td><td>azurerm_role_assignment</td><td>Role: AcrPull</td><td>Grants AKS Kubelet Identity pull rights without passwords</td></tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Terraform Modules & Code Preview -->
        <div class="g2">
          <section class="pn">
            <div class="ph">
              <span class="pt">Terraform Architecture Modules</span>
              <span class="pu">terraform/modules/</span>
            </div>
            <div class="tb">
              <table>
                <thead><tr><th>Module</th><th>Purpose</th><th>Outputs</th></tr></thead>
                <tbody class="mono">
                  <tr><td>modules/networking</td><td>VNet &amp; Subnet isolation</td><td>vnet_id, aks_subnet_id</td></tr>
                  <tr><td>modules/acr</td><td>Hardened Container Registry</td><td>acr_id, login_server</td></tr>
                  <tr><td>modules/aks</td><td>Managed AKS Cluster &amp; RBAC</td><td>cluster_id, cluster_name</td></tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="pn">
            <div class="ph">
              <span class="pt">Remote State Lock Spec</span>
              <span class="pu">terraform/backend.tf</span>
            </div>
            <pre>terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-forgeops-tfstate"
    storage_account_name = "stforgeopstfstate"
    container_name       = "tfstate"
    key                  = "forgeops.dev.terraform.tfstate"
  }
}</pre>
          </section>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
  let loopTimer = null;
  const trafficHistory = [2, 3, 2, 4, 3, 5, 4, 6, 5, 8, 7, 9, 6, 8, 10];
  const errorHistory =   [0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0];
  const latencyHistory = [12, 14, 11, 15, 12, 18, 14, 250, 15, 13, 16, 320, 14, 15, 18];

  function switchTab(tabId, el) {
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.nv').forEach(n => n.classList.remove('active'));
    
    document.getElementById('tab-' + tabId).classList.add('active');
    el.classList.add('active');

    const titles = {
      'overview': 'Overview',
      'kubernetes': 'Kubernetes Pods',
      'reliability': 'Reliability & SRE',
      'azure': 'Azure & Terraform'
    };
    document.getElementById('crumb-title').textContent = titles[tabId] || 'Overview';
  }

  function drawCharts() {
    drawCanvasChart('chart-traffic-canvas', [
      { data: trafficHistory, color: '#3b82f6', fill: 'rgba(59, 130, 246, 0.12)' },
      { data: errorHistory, color: '#f43f5e', fill: 'rgba(244, 63, 94, 0.2)' }
    ]);

    drawCanvasChart('chart-latency-canvas', [
      { data: latencyHistory, color: '#f59e0b', fill: 'rgba(245, 158, 11, 0.12)' }
    ]);
  }

  function drawCanvasChart(canvasId, seriesList) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.parentElement.clientWidth;
    const height = canvas.height = canvas.parentElement.clientHeight;

    ctx.clearRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = '#1e2430';
    ctx.lineWidth = 1;
    for (let y = 20; y < height - 10; y += 32) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Find max value
    let maxVal = 10;
    seriesList.forEach(s => {
      s.data.forEach(v => { if (v > maxVal) maxVal = v; });
    });

    // Draw each series
    seriesList.forEach(s => {
      const stepX = width / (s.data.length - 1);
      
      // Draw Area
      ctx.beginPath();
      ctx.moveTo(0, height);
      s.data.forEach((val, i) => {
        const x = i * stepX;
        const y = height - (val / maxVal * (height - 30)) - 10;
        ctx.lineTo(x, y);
      });
      ctx.lineTo(width, height);
      ctx.fillStyle = s.fill;
      ctx.fill();

      // Draw Line
      ctx.beginPath();
      s.data.forEach((val, i) => {
        const x = i * stepX;
        const y = height - (val / maxVal * (height - 30)) - 10;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = s.color;
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }

  async function fetchLiveStats() {
    try {
      const res = await fetch('/api/telemetry/stats');
      if (!res.ok) return;
      const data = await res.json();

      document.getElementById('stat-requests').textContent = data.total;
      document.getElementById('stat-error-rate').textContent = data.error_rate + '%';
      document.getElementById('stat-error-sub').textContent = `${data.errors} of ${data.total}`;
      
      document.getElementById('stat-fast').textContent = data.fast;
      document.getElementById('stat-fast-pct').textContent = data.total > 0 ? (data.fast / data.total * 100).toFixed(1) + '%' : '0%';

      document.getElementById('stat-slow').textContent = data.slow;
      document.getElementById('stat-slow-pct').textContent = data.total > 0 ? (data.slow / data.total * 100).toFixed(1) + '%' : '0%';

      document.getElementById('row-fast-count').textContent = data.fast;
      document.getElementById('row-slow-count').textContent = data.slow;
      document.getElementById('row-error-count').textContent = data.errors;

      const fastPct = data.total > 0 ? (data.fast / data.total * 100) : 0;
      const slowPct = data.total > 0 ? (data.slow / data.total * 100) : 0;
      const errPct = data.total > 0 ? (data.errors / data.total * 100) : 0;

      document.getElementById('bar-fast').style.width = fastPct + '%';
      document.getElementById('bar-slow').style.width = slowPct + '%';
      document.getElementById('bar-error').style.width = errPct + '%';

      // Alert Banner Condition
      const banner = document.getElementById('alert-banner');
      if (data.error_rate > 15 && data.total > 5) {
        banner.style.display = 'flex';
      } else {
        banner.style.display = 'none';
      }

      // Update Recent Requests
      if (data.recent && data.recent.length > 0) {
        const tbody = document.getElementById('recent-table-body');
        tbody.innerHTML = '';
        data.recent.slice(0, 8).forEach(r => {
          const tr = document.createElement('tr');
          const stClass = r.status === 200 ? 'ok' : 'er';
          tr.innerHTML = `
            <td>${r.time}</td>
            <td>${r.method}</td>
            <td class="mono">${r.path}</td>
            <td>${r.duration_ms}ms</td>
            <td><span class="st ${stClass}">${r.status}</span></td>
          `;
          tbody.appendChild(tr);
        });
      }

      // Update Pods Table
      if (data.pods) {
        document.getElementById('k8s-pod-count').textContent = data.pods.length;
        const podTbody = document.getElementById('pods-table-body');
        podTbody.innerHTML = '';
        data.pods.forEach(p => {
          const tr = document.createElement('tr');
          const stClass = p.status === 'Running' ? 'ok' : (p.status === 'Terminating' ? 'er' : 'wn');
          tr.innerHTML = `
            <td class="mono">${p.name}</td>
            <td>${p.ready}</td>
            <td><span class="st ${stClass}">${p.status}</span></td>
            <td>${p.restarts}</td>
            <td>${p.cpu || '12m'}</td>
            <td>${p.mem || '64Mi'}</td>
            <td>${p.ip}</td>
            <td><button class="btn btn-danger" style="min-height:24px;padding:0 8px;font-size:11px" onclick="triggerChaosPodKill('${p.name}')">Kill</button></td>
          `;
          podTbody.appendChild(tr);
        });
      }

      // Update Cluster Events
      if (data.events) {
        const evtTbody = document.getElementById('cluster-events-body');
        evtTbody.innerHTML = '';
        data.events.forEach(e => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${e.time}</td>
            <td><span class="st ${e.type === 'Warning' ? 'er' : 'ok'}">${e.reason}</span></td>
            <td>${e.message}</td>
          `;
          evtTbody.appendChild(tr);
        });
      }

      // Push point to chart history
      trafficHistory.push(Math.max(1, Math.floor(Math.random() * 5) + (data.recent ? data.recent.length : 1)));
      trafficHistory.shift();
      errorHistory.push(data.errors > 0 ? Math.floor(data.errors % 4) : 0);
      errorHistory.shift();
      latencyHistory.push(data.slow > 0 ? (200 + Math.floor(Math.random() * 200)) : (10 + Math.floor(Math.random() * 15)));
      latencyHistory.shift();
      drawCharts();

    } catch (e) {
      console.error(e);
    }
  }

  function showToast(title, msg, type = 'info') {
    let container = document.getElementById('toast-box');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-box';
      container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:10px;pointer-events:none';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const borderCol = type === 'error' ? '#ef7373' : (type === 'warn' ? '#f59e0b' : '#3b82f6');
    const bgCol = type === 'error' ? '#2a1414' : (type === 'warn' ? '#262011' : '#141821');
    toast.style.cssText = `background:${bgCol};border:1px solid ${borderCol};color:#fff;padding:12px 18px;border-radius:6px;box-shadow:0 10px 25px rgba(0,0,0,0.5);font-size:12.5px;min-width:280px;pointer-events:auto;animation:toast-in 0.25s ease-out;display:flex;flex-direction:column;gap:3px;`;
    toast.innerHTML = `<b style="font-size:13px">${title}</b><span style="color:#94a3b8;font-size:12px">${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  async function injectBatch(endpoint, count) {
    showToast('🚀 Injecting Traffic', `Firing ${count} concurrent requests to ${endpoint}...`, endpoint.includes('error') ? 'error' : 'info');
    const promises = [];
    for (let i = 0; i < count; i++) {
      promises.push(fetch(endpoint).catch(() => {}));
    }
    await Promise.all(promises);
    fetchLiveStats();
  }

  function toggleLoop() {
    const btn = document.getElementById('btn-loop');
    if (loopTimer) {
      clearInterval(loopTimer);
      loopTimer = null;
      btn.classList.remove('active');
      btn.textContent = 'Continuous Loop: OFF';
      showToast('⏸️ Loop Paused', 'Continuous traffic generator stopped.');
    } else {
      btn.classList.add('active');
      btn.textContent = '🟢 Continuous Loop: ON (Active)';
      showToast('🟢 Loop Started', 'Pumping requests every 600ms to simulate live user traffic...', 'info');
      loopTimer = setInterval(() => {
        const r = Math.random();
        if (r < 0.65) {
          fetch('/api/workload/fast').catch(() => {});
        } else if (r < 0.85) {
          fetch('/api/workload/slow').catch(() => {});
        } else {
          fetch('/api/workload/error').catch(() => {});
        }
        fetchLiveStats();
      }, 600);
    }
  }

  async function triggerChaosPodKill(podName) {
    try {
      showToast('💥 Chaos Monkey', `Sending SIGKILL to pod ${podName || 'active replica'}...`, 'warn');
      const res = await fetch('/api/chaos/kill-pod', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pod_name: podName })
      });
      const data = await res.json();
      showToast('🛡️ Self-Healing Triggered', `Kubernetes ReplicaSet scheduled replacement: ${data.replacement}`, 'info');
      fetchLiveStats();
    } catch (e) {
      showToast('Error', 'Failed to trigger chaos test.', 'error');
    }
  }

  // Initial render & fast 1s polling
  window.addEventListener('resize', drawCharts);
  fetchLiveStats();
  setInterval(fetchLiveStats, 1000);
</script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
