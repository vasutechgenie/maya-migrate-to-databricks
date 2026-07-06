CREATE TABLE core.dim_product (
    product_key  BIGINT        NOT NULL,
    product_id   BIGINT        NOT NULL,
    product_name VARCHAR(200)  NULL,
    category     VARCHAR(80)   NULL,
    brand        VARCHAR(80)   NULL,
    unit_price   NUMERIC(12,2) NULL,
    load_dt      TIMESTAMP     NULL,
    CONSTRAINT pk_dim_product PRIMARY KEY (product_key)
);
