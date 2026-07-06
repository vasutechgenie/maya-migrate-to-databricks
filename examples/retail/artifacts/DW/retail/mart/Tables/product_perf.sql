CREATE TABLE mart.product_perf (
    product_key  BIGINT        NOT NULL,
    product_name VARCHAR(200)  NULL,
    category     VARCHAR(80)   NULL,
    units_sold   BIGINT        NULL,
    net_amount   NUMERIC(16,2) NULL,
    CONSTRAINT pk_product_perf PRIMARY KEY (product_key)
);
