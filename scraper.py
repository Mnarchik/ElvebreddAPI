import json
import re
import time
import unicodedata

SOURCE_URL = "https://elvebredd.com/adopt-me-calculator"
BASE_URL = "https://elvebredd.com"
PUSH_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,(".*?")\]\)</script>', re.S)

AGES = {"default": "rvalue", "neon": "nvalue", "mega": "mvalue"}
POTIONS = {"nopotion": "nopotion", "ride": "ride", "fly": "fly", "fly_ride": "fly&ride"}


def slugify(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fetch_raw():
    from curl_cffi import requests

    # plain requests/curl get a Cloudflare 403, chrome TLS impersonation gets through
    resp = requests.get(SOURCE_URL, impersonate="chrome", timeout=30)
    resp.raise_for_status()
    chunks = PUSH_PATTERN.findall(resp.text)
    payload = "".join(json.loads(c) for c in chunks)
    start = payload.find('{"initialPets"')
    if start == -1:
        raise RuntimeError("initialPets not found in page payload, site layout changed")
    data, _ = json.JSONDecoder().raw_decode(payload, start)
    return data


def normalize(raw):
    item = {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "slug": slugify(raw.get("name") or ""),
        "type": raw.get("type"),
        "rarity": raw.get("rarity"),
        "status": raw.get("status"),
        "image": BASE_URL + raw["image"] if raw.get("image") else None,
    }
    if "rvalue" in raw:
        values = {}
        for age, prefix in AGES.items():
            values[age] = {"base": raw.get(prefix)}
            for potion, suffix in POTIONS.items():
                values[age][potion] = raw.get(f"{prefix} - {suffix}")
        item["values"] = values
        item["category"] = {
            "default": raw.get("categoryd"),
            "neon": raw.get("categoryn"),
            "mega": raw.get("categorym"),
        }
    else:
        item["value"] = raw.get("value")
    return item


def scrape():
    data = fetch_raw()
    items = [normalize(r) for r in data["initialPets"] if not r.get("hidden")]
    return {
        "source": SOURCE_URL,
        "version": data.get("initialVersion"),
        "fetched_at": int(time.time()),
        "count": len(items),
        "items": items,
    }


def write_snapshot(path="data/values.json"):
    snap = scrape()
    try:
        with open(path) as f:
            old = json.load(f)
    except (OSError, ValueError):
        old = None
    # only rewrite when values actually change so the repo isn't spammed with commits
    if old and old["items"] == snap["items"] and old["version"] == snap["version"]:
        print("no changes,", snap["count"], "items")
        return False
    snap["updated_at"] = snap.pop("fetched_at")
    with open(path, "w") as f:
        json.dump(snap, f, separators=(",", ":"))
    print("wrote", snap["count"], "items, version", snap["version"])
    return True


if __name__ == "__main__":
    write_snapshot()
