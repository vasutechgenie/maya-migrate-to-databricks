-- DW-side ETL that populates the Sales Ops Console app DB from the Northwind DW gold.
-- MAYA retargets this to land into a Databricks Lakebase synced table fed from UC gold.
INSERT INTO app.orders_ops (order_date, customer_id, orders, units, revenue, status)
SELECT order_date,
       customer_id,
       orders,
       units,
       revenue,
       CASE WHEN revenue > 0 THEN 'open' ELSE 'hold' END AS status
FROM rdm.mart_sales_daily;
