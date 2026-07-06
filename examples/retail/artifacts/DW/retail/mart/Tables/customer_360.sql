CREATE TABLE mart.customer_360 (
    customer_key    BIGINT        NOT NULL,
    customer_name   VARCHAR(200)  NULL,
    region          VARCHAR(64)   NULL,
    segment         VARCHAR(32)   NULL,
    lifetime_net    NUMERIC(16,2) NULL,
    orders_count    BIGINT        NULL,
    last_order_date DATE          NULL,
    CONSTRAINT pk_customer_360 PRIMARY KEY (customer_key)
);
