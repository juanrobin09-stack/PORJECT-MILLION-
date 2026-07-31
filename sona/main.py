import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sona import __version__
from sona.api import ask, automations, benchmarks, organizations, reputation, signals
from sona.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Sona API",
    version=__version__,
    description=(
        "The customer signal layer. One canonical schema for every piece of "
        "customer feedback, AI enrichment, declarative automations, "
        "natural-language answers, and cross-industry benchmarks."
    ),
    lifespan=lifespan,
)

API_PREFIX = "/v1"
app.include_router(organizations.router, prefix=API_PREFIX)
app.include_router(signals.router, prefix=API_PREFIX)
app.include_router(ask.router, prefix=API_PREFIX)
app.include_router(automations.router, prefix=API_PREFIX)
app.include_router(benchmarks.router, prefix=API_PREFIX)
app.include_router(reputation.router, prefix=API_PREFIX)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}
