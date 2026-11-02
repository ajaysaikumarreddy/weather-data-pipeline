"""Optional: export Gold views to CSV (last 90 days). Preferred: connect Power BI directly to BigQuery."""
import csv
import logging

from google.cloud import bigquery

from config import BASE_DIR, BQ_GOLD, GCP_LOCATION, GCP_PROJECT_ID, cli

log = logging.getLogger("export_powerbi")


def run(run_date):
    out = BASE_DIR / "powerbi_export"
    out.mkdir(exist_ok=True)
    bq = bigquery.Client(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", run_date)])
    rows = bq.query(f"SELECT * FROM `{GCP_PROJECT_ID}.{BQ_GOLD}.v_weather_report` "
                    f"WHERE obs_date >= DATE_SUB(@d, INTERVAL 90 DAY)", job_config=cfg).result()
    path = out / "v_weather_report.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([c.name for c in rows.schema])
        n = 0
        for r in rows:
            w.writerow(r.values()); n += 1
    log.info("Exported %s rows -> %s", n, path)


if __name__ == "__main__":
    cli(run, "Export gold to CSV")
