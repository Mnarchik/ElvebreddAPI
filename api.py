import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("adopt-me-api")

DATA_PATH = "data/values.json"
SCRAPE_INTERVAL_SECONDS = 10 * 60


def run_scraper_safe():
    try:
        from scraper import write_snapshot

        updated = write_snapshot(path=DATA_PATH)
        logger.info(f"Background scrape complete. Updated: {updated}")
        return updated
    except Exception as e:
        logger.error(f"Error during background scrape: {e}")
        return False


async def schedule_scraper():
    while True:
        await asyncio.to_thread(run_scraper_safe)
        await asyncio.sleep(SCRAPE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(DATA_PATH):
        logger.info("values.json not found on startup, scraping immediately...")
        await asyncio.to_thread(run_scraper_safe)

    task = asyncio.create_task(schedule_scraper())
    yield
    task.cancel()


app = FastAPI(
    title="Adopt Me Values API",
    description="REST API serving data scraped from Elvebredd",
    version="1.0.0",
    lifespan=lifespan,
)


def load_dataset():
    if not os.path.exists(DATA_PATH):
        raise HTTPException(
            status_code=503,
            detail="Values data not ready yet. Please try again shortly.",
        )
    with open(DATA_PATH, "r") as f:
        return json.load(f)


@app.get("/health")
def health_check():
    data = load_dataset()
    return {
        "status": "ok",
        "version": data.get("version"),
        "item_count": data.get("count"),
        "source": data.get("source"),
    }


@app.get("/items")
def get_items(
    type: Optional[str] = Query(None, description="Filter by item type"),
    rarity: Optional[str] = Query(None, description="Filter by rarity"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    data = load_dataset()
    items = data.get("items", [])

    if type:
        items = [i for i in items if i.get("type", "").lower() == type.lower()]
    if rarity:
        items = [i for i in items if i.get("rarity", "").lower() == rarity.lower()]

    total_matched = len(items)
    paginated_items = items[offset : offset + limit]

    return {
        "total": total_matched,
        "offset": offset,
        "limit": limit,
        "items": paginated_items,
    }


@app.get("/items/{slug}")
def get_item_by_slug(slug: str):
    data = load_dataset()
    items = data.get("items", [])

    slug_lower = slug.lower()
    for item in items:
        if item.get("slug") == slug_lower:
            return item

    raise HTTPException(status_code=404, detail=f"Item with slug '{slug}' not found")


@app.post("/refresh")
async def trigger_refresh():
    updated = await asyncio.to_thread(run_scraper_safe)
    return {"status": "success", "updated": updated}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
    
