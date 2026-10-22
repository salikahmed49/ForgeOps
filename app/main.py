
from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from time import perf_counter

app = FastAPI(
    title="DevOps Automation Platform",
    version="1.0.0",
)

REQUESTS = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)

LATENCY = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "path"],
)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    path = request.url.path

    if path != "/metrics":
        REQUESTS.labels(
            request.method, path, str(response.status_code)
        ).inc()

        LATENCY.labels(
            request.method, path
        ).observe(perf_counter() - start)

    return response


@app.get("/")
def root():
    return {
        "message": "DevOps Automation Platform is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
