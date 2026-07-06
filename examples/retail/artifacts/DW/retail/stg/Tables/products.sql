CREATE TABLE stg.products (
    product_id   BIGINT        NOT NULL,
    product_name VARCHAR(200)  NULL,
    category     VARCHAR(80)   NULL,
    brand        VARCHAR(80)   NULL,
    unit_price   NUMERIC(12,2) NULL,
    load_dt      TIMESTAMP     NULL,
    CONSTRAINT pk_stg_products PRIMARY KEY (product_id)
);
