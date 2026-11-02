"""
Orchestrator (simple stand-in for an Airflow DAG).
  python run_pipeline.py                      # yesterday
  python run_pipeline.py --date 2025-06-03
  python run_pipeline.py --backfill-start 2025-05-01 --backfill-end 2025-05-31
api_to_gcs -> gcs_to_bigquery (bronze) -> transform (silver, gold) -> export_powerbi
Every step is idempotent and retried 3x. Final failure alerts and exits non-zero.
"""
import argparse
import json
import logging
import sys
import time
import urllib.request
from datetime import timedelta

import config

config.setup_logging()
import api_to_gcs, export_powerbi, gcs_to_bigquery, transform_bigquery  # noqa: E402

log = logging.getLogger("pipeline")
STEPS = [("api_to_gcs", api_to_gcs.run), ("gcs_to_bigquery_bronze", gcs_to_bigquery.run),
         ("bq_silver_gold", transform_bigquery.run), ("export_powerbi", export_powerbi.run)]


def alert(msg):
    log.error(msg)
    with open(config.BASE_DIR / "logs" / "failed_runs.log", "a") as f:
        f.write(msg + "\n")
    if config.ALERT_WEBHOOK_URL:
        try:
            req = urllib.request.Request(config.ALERT_WEBHOOK_URL, json.dumps({"text": msg}).encode(),
                                         {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            log.warning("Webhook failed: %s", e)


def run_step(name, fn, run_date, retries=3, delay=30):
    for attempt in range(1, retries + 1):
        try:
            t0 = time.time()
            log.info(">>> %s (attempt %s/%s) for %s", name, attempt, retries, run_date)
            fn(run_date)
            log.info("<<< %s OK in %.1fs", name, time.time() - t0)
            return
        except Exception as e:
            log.exception("Step %s failed: %s", name, e)
            if attempt == retries:
                raise
            time.sleep(delay)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date"); p.add_argument("--backfill-start"); p.add_argument("--backfill-end")
    a = p.parse_args()
    if a.backfill_start:
        d, end = config.parse_date(a.backfill_start), config.parse_date(a.backfill_end or a.backfill_start)
        days = [d + timedelta(n) for n in range((end - d).days + 1)]
    else:
        days = [config.parse_date(a.date)]
    try:
        for day in days:
            for name, fn in STEPS:
                run_step(name, fn, day)
        log.info("PIPELINE SUCCESS for %s day(s)", len(days))
    except Exception as e:
        alert(f"[weather-pipeline] FAILED: {e}")
        sys.exit(1)
