"""FastAPI factory: CORS allow-all, health, openapi.json, ingest router, uvicorn entry."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.ingest import router as ingest_router
from backend.api.ingest import ws_router as ws_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # type: ignore[no-untyped-def]
    # auto-start watchdog poll 30s on startup (non-blocking Observer thread)
    try:
        from backend.api.ingest import start_watchdog

        start_watchdog(poll_dir="data/raw/watch/inbox", interval=30)
    except Exception:
        pass
    yield
    try:
        from backend.api.ingest import stop_watchdog

        stop_watchdog()
    except Exception:
        pass


app = FastAPI(
    title="SIH26146 Bitcoin Transaction Traffic API",
    version="1.0.0",
    description="M1 ingest routes per PROTOTYPE_DECISIONS_FINAL §2 Part1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(ws_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
