CREATE VIEW serving.v_exec_kpis AS
SELECT sales_date, region, SUM(revenue) AS revenue, SUM(orders) AS orders
FROM rdm.mart_sales_daily
GROUP BY sales_date, region;
