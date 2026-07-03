CREATE TABLE rdm.mart_product_perf (
    product_key  BIGINT        NOT NULL,
    supplier_key BIGINT        NULL,
    category     VARCHAR(64)   NULL,
    units_sold   INT           NULL,
    revenue      DECIMAL(18,2) NULL,
    return_rate  DECIMAL(9,4)  NULL,
    load_dt      DATETIME2     NULL,
    CONSTRAINT PK_mart_product_perf PRIMARY KEY (product_key)
);
