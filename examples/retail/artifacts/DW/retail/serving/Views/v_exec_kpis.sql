CREATE VIEW serving.v_exec_kpis AS
SELECT cal_date,
       SUM(net_amount)  AS net_amount,
       SUM(order_count) AS order_count
FROM serving.sales_daily
GROUP BY cal_date;
