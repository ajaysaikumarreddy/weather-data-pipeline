"""Shared config + helpers."""
import argparse
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "US")
GCS_BUCKET = os.getenv("GCS_BUCKET") or f"{GCP_PROJECT_ID}-weather-raw"
BQ_BRONZE, BQ_SILVER, BQ_GOLD = "weather_bronze", "weather_silver", "weather_gold"
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

# Cities we pull from the API (name, lat, lon). Add your own!
CITIES = [
    ("Hyderabad", 17.3850, 78.4867), ("Mumbai", 19.0760, 72.8777),
    ("Delhi", 28.6139, 77.2090), ("Bengaluru", 12.9716, 77.5946),
    ("London", 51.5072, -0.1276), ("New York", 40.7128, -74.0060),
    ("Tokyo", 35.6762, 139.6503), ("Sydney", -33.8688, 151.2093),
]
HOURLY_VARS = ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"]


def setup_logging():
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(BASE_DIR / "logs" / "pipeline.log")],
    )


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else date.today() - timedelta(days=1)


def cli(run_fn, description):
    """Every step can run alone:  python step.py --date 2025-06-03"""
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--date", help="YYYY-MM-DD (default: yesterday)")
    a = p.parse_args()
    setup_logging()
    run_fn(parse_date(a.date))
