CREATE VIEW core.v_active_customers AS
SELECT customer_key, customer_id, customer_name, region, segment
FROM core.dim_customer
WHERE is_active = true;
