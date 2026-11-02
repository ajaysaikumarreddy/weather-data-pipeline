# API → GCS → BigQuery (bronze/silver/gold) → Power BI

Source: Open-Meteo REST API (free, no key). Hourly weather for 8 cities, loaded daily.

    Open-Meteo API ──▶ GCS (raw JSON) ──▶ BigQuery bronze ──▶ silver (parsed, cleaned) ──▶ gold (KPIs, views) ──▶ Power BI

Setup (run from C:\dev\weather-pipeline, NOT inside OneDrive):
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env        # set GCP_PROJECT_ID
    gcloud auth application-default login
    python setup_gcp.py

Run one step at a time (learn each hop), then all together:
    python api_to_gcs.py --date 2025-06-03
    python gcs_to_bigquery.py --date 2025-06-03
    python transform_bigquery.py --date 2025-06-03
    python run_pipeline.py --backfill-start 2025-05-01 --backfill-end 2025-05-31
    python run_pipeline.py                       # yesterday (schedule this daily)

BigQuery needs billing enabled (DELETE/INSERT are blocked in the free Sandbox).
Power BI: Get Data > Google BigQuery > weather_gold > v_weather_report.
