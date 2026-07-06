CREATE TABLE stg.sales (
    sale_id     BIGINT      NOT NULL,
    store_id    BIGINT      NULL,
    customer_id BIGINT      NULL,
    sale_ts     TIMESTAMP   NULL,
    channel     VARCHAR(24) NULL,
    load_dt     TIMESTAMP   NULL,
    CONSTRAINT pk_stg_sales PRIMARY KEY (sale_id)
);
