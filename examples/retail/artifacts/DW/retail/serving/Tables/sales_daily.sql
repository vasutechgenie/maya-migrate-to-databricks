CREATE TABLE serving.sales_daily (
    cal_date    DATE          NOT NULL,
    region      VARCHAR(64)   NOT NULL,
    net_amount  NUMERIC(16,2) NULL,
    order_count BIGINT        NULL,
    CONSTRAINT pk_sales_daily PRIMARY KEY (cal_date, region)
);
