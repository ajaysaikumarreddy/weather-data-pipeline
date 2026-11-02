"""STEP 3 - Bronze -> Silver (parse + clean JSON) -> Gold (daily KPIs + report views)."""
import logging

from google.cloud import bigquery

from config import (BASE_DIR, BQ_BRONZE, BQ_GOLD, BQ_SILVER, CITIES, GCP_LOCATION, GCP_PROJECT_ID, cli)

log = logging.getLogger("transform_bigquery")
SQL_FILES = ["silver_weather_hourly.sql", "gold_daily_city_weather.sql", "gold_views.sql"]


def _render(sql):
    return (sql.replace("{{PROJECT}}", GCP_PROJECT_ID).replace("{{BRONZE}}", BQ_BRONZE)
               .replace("{{SILVER}}", BQ_SILVER).replace("{{GOLD}}", BQ_GOLD))


def run(run_date):
    bq = bigquery.Client(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("run_date", "DATE", run_date)])
    for name in SQL_FILES:
        job = bq.query(_render((BASE_DIR / "sql" / name).read_text()), job_config=cfg)
        job.result()
        log.info("Ran %-32s (%.2f MB processed)", name, (job.total_bytes_processed or 0) / 1e6)

    # data-quality gate: expect 24 hourly rows per city
    q = bq.query(f"SELECT COUNT(*) c FROM `{GCP_PROJECT_ID}.{BQ_SILVER}.weather_hourly` WHERE obs_date = @run_date",
                 job_config=cfg)
    n = list(q.result())[0].c
    expected = 24 * len(CITIES)
    if n == 0:
        raise ValueError("Silver produced 0 rows")
    if n < expected:
        log.warning("DQ WARNING: silver has %s rows, expected %s (missing/invalid hours dropped)", n, expected)
    log.info("Silver rows for %s: %s", run_date, n)


if __name__ == "__main__":
    cli(run, "Bronze -> Silver -> Gold")
