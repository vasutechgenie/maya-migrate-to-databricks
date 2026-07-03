CREATE TABLE sales.fact_order (
    order_key     BIGINT        NOT NULL,
    order_id      BIGINT        NOT NULL,
    order_line_id BIGINT        NOT NULL,
    customer_key  BIGINT        NULL,
    product_key   BIGINT        NULL,
    order_date    DATE          NULL,
    qty           INT           NULL,
    amount        DECIMAL(18,2) NULL,
    discount      DECIMAL(9,4)  NULL,
    load_dt       DATETIME2     NULL,
    CONSTRAINT PK_fact_order PRIMARY KEY (order_key)
);
