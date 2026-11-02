-- SILVER: explode the raw JSON arrays into one clean row per city per hour.
CREATE TABLE IF NOT EXISTS `{{PROJECT}}.{{SILVER}}.weather_hourly` (
  city STRING, obs_ts TIMESTAMP, obs_date DATE,
  temp_c FLOAT64, temp_f FLOAT64, humidity_pct FLOAT64, precipitation_mm FLOAT64, wind_kmh FLOAT64,
  ingested_at TIMESTAMP, silver_loaded_at TIMESTAMP
) PARTITION BY obs_date CLUSTER BY city;

DELETE FROM `{{PROJECT}}.{{SILVER}}.weather_hourly` WHERE obs_date = @run_date;

INSERT INTO `{{PROJECT}}.{{SILVER}}.weather_hourly`
WITH parsed AS (
  SELECT
    TRIM(b.city) AS city,
    PARSE_TIMESTAMP('%Y-%m-%dT%H:%M', t) AS obs_ts,
    SAFE_CAST(JSON_VALUE_ARRAY(b.payload, '$.hourly.temperature_2m')[SAFE_OFFSET(i)] AS FLOAT64)       AS temp_c,
    SAFE_CAST(JSON_VALUE_ARRAY(b.payload, '$.hourly.relative_humidity_2m')[SAFE_OFFSET(i)] AS FLOAT64) AS humidity_pct,
    SAFE_CAST(JSON_VALUE_ARRAY(b.payload, '$.hourly.precipitation')[SAFE_OFFSET(i)] AS FLOAT64)        AS precipitation_mm,
    SAFE_CAST(JSON_VALUE_ARRAY(b.payload, '$.hourly.wind_speed_10m')[SAFE_OFFSET(i)] AS FLOAT64)       AS wind_kmh,
    b.ingested_at
  FROM `{{PROJECT}}.{{BRONZE}}.weather_raw` b,
       UNNEST(JSON_VALUE_ARRAY(b.payload, '$.hourly.time')) AS t WITH OFFSET i
  WHERE b.run_date = @run_date
)
SELECT city, obs_ts, DATE(obs_ts), temp_c, ROUND(temp_c * 9 / 5 + 32, 1), humidity_pct,
       GREATEST(precipitation_mm, 0), wind_kmh, ingested_at, CURRENT_TIMESTAMP()
FROM parsed
WHERE DATE(obs_ts) = @run_date
  AND temp_c BETWEEN -60 AND 60                       -- drop impossible / null readings
  AND (humidity_pct IS NULL OR humidity_pct BETWEEN 0 AND 100)
QUALIFY ROW_NUMBER() OVER (PARTITION BY city, obs_ts ORDER BY ingested_at DESC) = 1;
