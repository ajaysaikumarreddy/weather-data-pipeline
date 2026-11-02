-- Reporting view for Power BI: adds trend metrics with window functions
CREATE OR REPLACE VIEW `{{PROJECT}}.{{GOLD}}.v_weather_report` AS
SELECT d.*,
  DATE_TRUNC(obs_date, MONTH) AS month_start,
  ROUND(AVG(avg_temp_c) OVER (PARTITION BY city ORDER BY obs_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS temp_7d_avg_c,
  ROUND(avg_temp_c - LAG(avg_temp_c) OVER (PARTITION BY city ORDER BY obs_date), 1) AS temp_change_vs_prev_day,
  RANK() OVER (PARTITION BY obs_date ORDER BY avg_temp_c DESC) AS hottest_rank_in_day
FROM `{{PROJECT}}.{{GOLD}}.daily_city_weather` d;
