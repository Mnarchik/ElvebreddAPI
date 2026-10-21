import json
import os
import re
import time
import unicodedata

SOURCE_URL = "https://elvebredd.com/adopt-me-calculator[span_0](start_span)"[span_0](end_span)
BASE_URL = "https://elvebredd.com[span_1](start_span)"[span_1](end_span)
PUSH_PATTERN = re.compile(r'self\.__next_f\.push\(\[1,(".*?")\]\)</script>', re.S)[span_2](start_span)[span_2](end_span)

AGES = {"default": "rvalue", "neon": "nvalue", "mega": "mvalue"}[span_3](start_span)[span_3](end_span)
POTIONS = {"nopotion": "nopotion", "ride": "ride", "fly": "fly", "fly_ride": "fly&ride"}[span_4](start_span)[span_4](end_span)


def slugify(name):
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()[span_5](start_span)[span_5](end_span)
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[span_6](start_span)[span_6](end_span)


def fetch_raw():
    import cloudscraper

    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "android",
            "desktop": False,
        }
    )
    resp = scraper.get(SOURCE_URL, timeout=30)
    resp.raise_for_status()
    chunks = PUSH_PATTERN.findall(resp.text)
    payload = "".join(json.loads(c) for c in chunks)
    start = payload.find('{"initialPets"')
    if start == -1:
        raise RuntimeError("initialPets not found in page payload, site layout changed")[span_7](start_span)[span_7](end_span)
    data, _ = json.JSONDecoder().raw_decode(payload, start)
    return data


def normalize(raw):
    item = {
        "id": raw.get("id"),[span_8](start_span)[span_8](end_span)
        "name": raw.get("name"),[span_9](start_span)[span_9](end_span)
        "slug": slugify(raw.get("name") or ""),[span_10](start_span)[span_10](end_span)
        "type": raw.get("type"),[span_11](start_span)[span_11](end_span)
        "rarity": raw.get("rarity"),[span_12](start_span)[span_12](end_span)
        "status": raw.get("status"),[span_13](start_span)[span_13](end_span)
        "image": BASE_URL + raw["image"] if raw.get("image") else None,[span_14](start_span)[span_14](end_span)
    }
    if "rvalue" in raw:[span_15](start_span)[span_15](end_span)
        values = {}[span_16](start_span)[span_16](end_span)
        for age, prefix in AGES.items():[span_17](start_span)[span_17](end_span)
            values[age] = {"base": raw.get(prefix)}[span_18](start_span)[span_18](end_span)
            for potion, suffix in POTIONS.items():[span_19](start_span)[span_19](end_span)
                values[age][potion] = raw.get(f"{prefix} - {suffix}")[span_20](start_span)[span_20](end_span)
        item["values"] = values[span_21](start_span)[span_21](end_span)
        item["category"] = {
            "default": raw.get("categoryd"),[span_22](start_span)[span_22](end_span)
            "neon": raw.get("categoryn"),[span_23](start_span)[span_23](end_span)
            "mega": raw.get("categorym"),[span_24](start_span)[span_24](end_span)
        }
    else:
        item["value"] = raw.get("value")[span_25](start_span)[span_25](end_span)
    return item


def scrape():
    data = fetch_raw()[span_26](start_span)[span_26](end_span)
    items = [normalize(r) for r in data["initialPets"] if not r.get("hidden")][span_27](start_span)[span_27](end_span)
    return {
        "source": SOURCE_URL,[span_28](start_span)[span_28](end_span)
        "version": data.get("initialVersion"),[span_29](start_span)[span_29](end_span)
        "fetched_at": int(time.time()),[span_30](start_span)[span_30](end_span)
        "count": len(items),[span_31](start_span)[span_31](end_span)
        "items": items,[span_32](start_span)[span_32](end_span)
    }


def write_snapshot(path="data/values.json"):[span_33](start_span)[span_33](end_span)
    snap = scrape()[span_34](start_span)[span_34](end_span)
    try:
        with open(path) as f:[span_35](start_span)[span_35](end_span)
            old = json.load(f)[span_36](start_span)[span_36](end_span)
    except (OSError, ValueError):
        old = None[span_37](start_span)[span_37](end_span)

    # Only rewrite when values actually change
    if old and old.get("items") == snap["items"] and old.get("version") == snap["version"]:
        print("no changes,", snap["count"], "items")[span_38](start_span)[span_38](end_span)
        return False[span_39](start_span)[span_39](end_span)

    snap["updated_at"] = snap.pop("fetched_at")[span_40](start_span)[span_40](end_span)

    # Automatically create the destination directory if missing
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w") as f:[span_41](start_span)[span_41](end_span)
        json.dump(snap, f, separators=(",", ":"))[span_42](start_span)[span_42](end_span)
    print("wrote", snap["count"], "items, version", snap["version"])[span_43](start_span)[span_43](end_span)
    return True[span_44](start_span)[span_44](end_span)


if __name__ == "__main__":
    write_snapshot()[span_45](start_span)[span_45](end_span)
