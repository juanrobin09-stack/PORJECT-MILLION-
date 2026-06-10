import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.database import init_db
from app.routers import insights, locations, organizations, responses, reviews

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Resona API",
    version=__version__,
    description=(
        "The AI reputation engine. Ingest reviews, get on-brand responses, "
        "structured sentiment intelligence, and reputation risk alerts."
    ),
    lifespan=lifespan,
)

API_PREFIX = "/v1"
app.include_router(organizations.router, prefix=API_PREFIX)
app.include_router(locations.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)
app.include_router(responses.router, prefix=API_PREFIX)
app.include_router(insights.router, prefix=API_PREFIX)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "version": __version__}
