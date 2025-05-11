from fastapi import FastAPI
from Parser import scrape_board
import asyncio, logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

REFRESH_MIN = 3
log = logging.getLogger("uvicorn.error")

async def scrape_async(kind: str):
    """Запускает sync-scraper в отдельном потоке."""
    return await asyncio.to_thread(scrape_board, kind)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = {"departures": [], "arrivals": [], "ts": None}

    # ── 1. блокирующая (но теперь async) инициализация ──────────────────
    log.info("⌛ Initial scraping…")
    for kind in ("departures", "arrivals"):
        try:
            cache[kind] = await scrape_async(kind)
            log.info("✓ %s %d rows", kind, len(cache[kind]))
        except Exception as e:
            log.error("first scrape %s failed: %s", kind, e)
    cache["ts"] = datetime.now(timezone.utc)

    # ── 2. фон-лооп ───────────────────────────────────────────────────────
    async def refresher():
        while True:
            for kind in ("departures", "arrivals"):
                try:
                    cache[kind] = await scrape_async(kind)
                    log.info("✓ refreshed %s (%d rows)", kind, len(cache[kind]))
                except Exception as e:
                    log.error("refresh %s failed: %s", kind, e)
            cache["ts"] = datetime.now(timezone.utc)
            await asyncio.sleep(REFRESH_MIN * 60)

    task = asyncio.create_task(refresher())
    app.state.cache = cache
    try:
        yield
    finally:
        task.cancel()

app = FastAPI(title="MCX Flight Board API", lifespan=lifespan)

@app.get("/flights/{kind}")
def get_flights(kind: str):
    if kind not in ("departures", "arrivals"):
        return {"error": "bad kind"}
    c = app.state.cache
    return {"last_update_utc": c["ts"], "data": c[kind]}
