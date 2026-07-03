CREATE VIEW sales.v_active_customers AS
SELECT customer_key, customer_id, customer_name, region, segment
FROM sales.dim_customer
WHERE is_active = 1;
