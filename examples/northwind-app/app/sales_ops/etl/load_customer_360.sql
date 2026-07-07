-- Populates the customer_360 read-model from the Northwind DW gold customer mart.
INSERT INTO app.customer_360 (customer_id, customer_name, region, lifetime_revenue,
                             last_order_date, web_sessions_30d)
SELECT customer_id,
       customer_name,
       region,
       lifetime_revenue,
       last_order_date,
       web_sessions_30d
FROM rdm.mart_customer_360;
