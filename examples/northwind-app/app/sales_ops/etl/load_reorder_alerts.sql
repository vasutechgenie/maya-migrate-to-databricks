-- Populates the reorder_alerts read-model from the Northwind DW product-performance mart.
INSERT INTO app.reorder_alerts (product_id, product_name, supplier, units_on_hand,
                               reorder_point, alert)
SELECT product_id,
       product_name,
       supplier,
       units_on_hand,
       reorder_point,
       CASE WHEN units_on_hand < reorder_point THEN 1 ELSE 0 END AS alert
FROM rdm.mart_product_perf;
