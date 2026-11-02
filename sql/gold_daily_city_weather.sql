-- GOLD: one row per city per day with business-friendly KPIs
CREATE TABLE IF NOT EXISTS `{{PROJECT}}.{{GOLD}}.daily_city_weather` (
  obs_date DATE, city STRING, avg_temp_c FLOAT64, min_temp_c FLOAT64, max_temp_c FLOAT64,
  temp_range_c FLOAT64, avg_humidity_pct FLOAT64, total_precip_mm FLOAT64, rainy_hours INT64,
  max_wind_kmh FLOAT64, comfort_category STRING, hours_observed INT64, gold_loaded_at TIMESTAMP
) PARTITION BY obs_date CLUSTER BY city;

DELETE FROM `{{PROJECT}}.{{GOLD}}.daily_city_weather` WHERE obs_date = @run_date;

INSERT INTO `{{PROJECT}}.{{GOLD}}.daily_city_weather`
SELECT obs_date, city,
  ROUND(AVG(temp_c), 1), ROUND(MIN(temp_c), 1), ROUND(MAX(temp_c), 1), ROUND(MAX(temp_c) - MIN(temp_c), 1),
  ROUND(AVG(humidity_pct), 1), ROUND(SUM(precipitation_mm), 2),
  COUNTIF(precipitation_mm > 0), ROUND(MAX(wind_kmh), 1),
  CASE WHEN AVG(temp_c) < 10 THEN 'Cold'
       WHEN AVG(temp_c) < 22 THEN 'Mild'
       WHEN AVG(temp_c) < 32 THEN 'Warm' ELSE 'Hot' END,
  COUNT(*), CURRENT_TIMESTAMP()
FROM `{{PROJECT}}.{{SILVER}}.weather_hourly`
WHERE obs_date = @run_date
GROUP BY obs_date, city;
