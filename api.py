import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
import uvicorn

app = FastAPI(
    title="Adopt Me Values API",
    description="REST API serving data scraped from Elvebredd",
    version="1.0.0",
)

DATA_PATH = "data/values.json"


def load_dataset():
    """Helper function to load the latest snapshot."""
    if not os.path.exists(DATA_PATH):
        raise HTTPException(
            status_code=503,
            detail="Values data not found. Please run scraper.py first.",
        )
    with open(DATA_PATH, "r") as f:
        return json.load(f)


@app.get("/health")
def health_check():
    """Health and metadata endpoint."""
    data = load_dataset()
    return {
        "status": "ok",
        "version": data.get("version"),
        "item_count": data.get("count"),
        "source": data.get("source"),
    }


@app.get("/items")
def get_items(
    type: Optional[str] = Query(
        None,
        description="Filter by item type (e.g. 'pets', 'toys', 'vehicles')",
    ),
    rarity: Optional[str] = Query(
        None,
        description="Filter by rarity (e.g. 'legendary', 'ultra rare')",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve items with optional filtering and pagination."""
    data = load_dataset()
    items = data.get("items", [])

    if type:
        items = [i for i in items if i.get("type", "").lower() == type.lower()]
    if rarity:
        items = [
            i for i in items if i.get("rarity", "").lower() == rarity.lower()
        ]

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
    """Fetch a single item by its URL slug (e.g. 'bat-dragon', 'shadow-dragon')."""
    data = load_dataset()
    items = data.get("items", [])

    slug_lower = slug.lower()
    for item in items:
        if item.get("slug") == slug_lower:
            return item

    raise HTTPException(
        status_code=404, detail=f"Item with slug '{slug}' not found"
    )


@app.post("/refresh")
def trigger_refresh():
    """Triggers the scraper to update values.json from the live website."""
    try:
        from scraper import write_snapshot

        updated = write_snapshot()
        return {"status": "success", "updated": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
  
