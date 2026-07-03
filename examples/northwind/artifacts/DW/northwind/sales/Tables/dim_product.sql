CREATE TABLE sales.dim_product (
    product_key   BIGINT        NOT NULL,
    product_id    BIGINT        NOT NULL,
    product_name  VARCHAR(200)  NULL,
    category      VARCHAR(64)   NULL,
    supplier_key  BIGINT        NULL,
    unit_price    DECIMAL(18,2) NULL,
    load_dt       DATETIME2     NULL,
    CONSTRAINT PK_dim_product PRIMARY KEY (product_key)
);
