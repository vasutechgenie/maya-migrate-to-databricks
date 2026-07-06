CREATE TABLE core.fact_web_orders (
    web_order_key BIGINT        NOT NULL,
    web_order_id  BIGINT        NOT NULL,
    date_key      INT           NULL,
    customer_key  BIGINT        NULL,
    product_key   BIGINT        NULL,
    qty           INT           NULL,
    net_amount    NUMERIC(14,2) NULL,
    load_dt       TIMESTAMP     NULL,
    CONSTRAINT pk_fact_web_orders PRIMARY KEY (web_order_key)
);
