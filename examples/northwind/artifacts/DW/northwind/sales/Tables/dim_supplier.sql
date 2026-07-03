CREATE TABLE sales.dim_supplier (
    supplier_key  BIGINT       NOT NULL,
    supplier_id   BIGINT       NOT NULL,
    supplier_name VARCHAR(200) NULL,
    country       VARCHAR(64)  NULL,
    load_dt       DATETIME2    NULL,
    CONSTRAINT PK_dim_supplier PRIMARY KEY (supplier_key)
);
