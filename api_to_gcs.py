"""
STEP 1 - Call the Open-Meteo REST API (no key needed) for one day, for every city,
and land the RAW responses in GCS as newline-delimited JSON (one line per city).

  gs://<bucket>/weather/run_date=YYYY-MM-DD/weather_YYYYMMDD.ndjson

Each line wraps the untouched API response as a JSON *string* in `payload`,
so Bronze stays raw and Silver can parse it with SQL (ELT).
Idempotent: re-running the same date overwrites the same file.
"""
import json
import logging
import time
from datetime import date, datetime, timedelta, timezone

import requests
from google.cloud import storage

from config import CITIES, GCP_PROJECT_ID, GCS_BUCKET, HOURLY_VARS, cli

log = logging.getLogger("api_to_gcs")
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"          # recent days (last ~90)
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"     # older history


def fetch_city(name, lat, lon, run_date, retries=4):
    url = ARCHIVE_URL if run_date < date.today() - timedelta(days=80) else FORECAST_URL
    params = {"latitude": lat, "longitude": lon, "start_date": run_date.isoformat(),
              "end_date": run_date.isoformat(), "hourly": ",".join(HOURLY_VARS), "timezone": "UTC"}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:     # rate-limited / server error -> backoff
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            data = r.json()
            if "hourly" not in data:
                raise ValueError(f"No 'hourly' in response for {name}: {str(data)[:200]}")
            return data
        except Exception as e:
            log.warning("%s attempt %s/%s failed: %s", name, attempt, retries, e)
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)


def run(run_date):
    ds = run_date.strftime("%Y%m%d")
    ingested_at = datetime.now(timezone.utc).isoformat()
    lines = []
    for name, lat, lon in CITIES:
        data = fetch_city(name, lat, lon, run_date)
        lines.append(json.dumps({
            "city": name, "latitude": lat, "longitude": lon, "run_date": run_date.isoformat(),
            "ingested_at": ingested_at, "payload": json.dumps(data)}))
        log.info("Fetched %s (%s hourly points)", name, len(data["hourly"]["time"]))
        time.sleep(0.5)                                          # be polite to a free API

    blob_name = f"weather/run_date={run_date.isoformat()}/weather_{ds}.ndjson"
    bucket = storage.Client(project=GCP_PROJECT_ID).bucket(GCS_BUCKET)
    bucket.blob(blob_name).upload_from_string("\n".join(lines) + "\n", content_type="application/x-ndjson")
    log.info("Uploaded gs://%s/%s (%s cities)", GCS_BUCKET, blob_name, len(lines))


if __name__ == "__main__":
    cli(run, "API -> GCS")
