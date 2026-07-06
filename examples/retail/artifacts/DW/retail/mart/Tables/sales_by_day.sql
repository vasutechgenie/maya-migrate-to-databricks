CREATE TABLE mart.sales_by_day (
    date_key        INT           NOT NULL,
    region          VARCHAR(64)   NOT NULL,
    gross_amount    NUMERIC(16,2) NULL,
    discount_amount NUMERIC(16,2) NULL,
    net_amount      NUMERIC(16,2) NULL,
    order_count     BIGINT        NULL,
    CONSTRAINT pk_sales_by_day PRIMARY KEY (date_key, region)
);
