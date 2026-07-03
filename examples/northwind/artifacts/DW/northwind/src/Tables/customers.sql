CREATE TABLE src.customers (
    customer_id   BIGINT       NOT NULL,
    customer_name VARCHAR(200) NULL,
    region        VARCHAR(64)  NULL,
    segment       VARCHAR(32)  NULL,
    created_ts    DATETIME2    NULL,
    load_dt       DATETIME2    NULL
);
