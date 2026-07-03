CREATE TABLE rdm.mart_sales_daily (
    sales_date  DATE          NOT NULL,
    region      VARCHAR(64)   NOT NULL,
    product_key BIGINT        NOT NULL,
    orders      INT           NULL,
    units       INT           NULL,
    revenue     DECIMAL(18,2) NULL,
    load_dt     DATETIME2     NULL,
    CONSTRAINT PK_mart_sales_daily PRIMARY KEY (sales_date, region, product_key)
);
