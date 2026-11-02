"""One-time: create the GCS bucket and the 3 BigQuery datasets."""
import logging

from google.cloud import bigquery, storage
from google.cloud.exceptions import Conflict

from config import BQ_BRONZE, BQ_GOLD, BQ_SILVER, GCP_LOCATION, GCP_PROJECT_ID, GCS_BUCKET, setup_logging

log = logging.getLogger("setup_gcp")


def run():
    gcs = storage.Client(project=GCP_PROJECT_ID)
    try:
        b = gcs.bucket(GCS_BUCKET)
        b.add_lifecycle_delete_rule(age=90)     # raw files auto-delete after 90 days
        gcs.create_bucket(b, location=GCP_LOCATION)
        log.info("Created bucket gs://%s", GCS_BUCKET)
    except Conflict:
        log.info("Bucket gs://%s already exists", GCS_BUCKET)

    bq = bigquery.Client(project=GCP_PROJECT_ID)
    for name in (BQ_BRONZE, BQ_SILVER, BQ_GOLD):
        ds = bigquery.Dataset(f"{GCP_PROJECT_ID}.{name}")
        ds.location = GCP_LOCATION
        bq.create_dataset(ds, exists_ok=True)
        log.info("Dataset ready: %s", name)


if __name__ == "__main__":
    setup_logging()
    run()
