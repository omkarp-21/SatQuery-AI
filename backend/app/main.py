"""SATQUERY API entrypoint.

Run: ``uvicorn app.main:app --reload``
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: warm model registry, open DB pool, connect object storage.
    yield
    # TODO: graceful shutdown.


app = FastAPI(
    title="SATQUERY",
    version="0.1.0",
    summary="Natural-language querying of satellite imagery with verifiable evidence.",
    lifespan=lifespan,
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


# TODO: app.include_router(...) from app.api once routes exist.
