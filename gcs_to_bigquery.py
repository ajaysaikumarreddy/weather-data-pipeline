"""STEP 2 - GCS -> BigQuery BRONZE (raw). Loads only the run date into its own partition."""
import logging

from google.cloud import bigquery

from config import BQ_BRONZE, CITIES, GCP_LOCATION, GCP_PROJECT_ID, GCS_BUCKET, cli

log = logging.getLogger("gcs_to_bigquery")

SCHEMA = [
    bigquery.SchemaField("city", "STRING"),
    bigquery.SchemaField("latitude", "FLOAT64"),
    bigquery.SchemaField("longitude", "FLOAT64"),
    bigquery.SchemaField("run_date", "DATE"),
    bigquery.SchemaField("ingested_at", "TIMESTAMP"),
    bigquery.SchemaField("payload", "STRING"),     # raw API JSON, parsed later in Silver
]


def run(run_date):
    ds = run_date.strftime("%Y%m%d")
    bq = bigquery.Client(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    table_id = f"{GCP_PROJECT_ID}.{BQ_BRONZE}.weather_raw"

    t = bigquery.Table(table_id, schema=SCHEMA)
    t.time_partitioning = bigquery.TimePartitioning(type_=bigquery.TimePartitioningType.DAY, field="run_date")
    bq.create_table(t, exists_ok=True)

    uri = f"gs://{GCS_BUCKET}/weather/run_date={run_date.isoformat()}/weather_{ds}.ndjson"
    cfg = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON, schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)      # overwrites just this partition
    bq.load_table_from_uri(uri, f"{table_id}${ds}", job_config=cfg).result()

    # reconcile: one raw row per city expected
    q = bq.query(f"SELECT COUNT(*) c FROM `{table_id}` WHERE run_date = @d",
                 job_config=bigquery.QueryJobConfig(
                     query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", run_date)]))
    loaded = list(q.result())[0].c
    if loaded != len(CITIES):
        raise ValueError(f"Expected {len(CITIES)} raw rows, found {loaded}")
    log.info("Bronze loaded: %s rows for %s", loaded, run_date)


if __name__ == "__main__":
    cli(run, "GCS -> BigQuery bronze")
