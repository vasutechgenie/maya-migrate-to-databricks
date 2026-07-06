CREATE TABLE stg.web_orders (
    web_order_id BIGINT        NOT NULL,
    customer_id  BIGINT        NULL,
    product_id   BIGINT        NULL,
    order_ts     TIMESTAMP     NULL,
    qty          INT           NULL,
    unit_price   NUMERIC(12,2) NULL,
    load_dt      TIMESTAMP     NULL,
    CONSTRAINT pk_stg_web_orders PRIMARY KEY (web_order_id)
);
