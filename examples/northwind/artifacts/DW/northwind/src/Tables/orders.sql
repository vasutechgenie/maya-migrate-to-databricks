CREATE TABLE src.orders (
    order_id    BIGINT      NOT NULL,
    customer_id BIGINT      NULL,
    order_date  DATE        NULL,
    status      VARCHAR(24) NULL,
    load_dt     DATETIME2   NULL
);
