CREATE TABLE serving.sales_daily (
    sales_date DATE          NOT NULL,
    region     VARCHAR(64)   NOT NULL,
    revenue    DECIMAL(18,2) NULL,
    orders     INT           NULL,
    units      INT           NULL,
    load_dt    DATETIME2     NULL,
    CONSTRAINT PK_serving_sales_daily PRIMARY KEY (sales_date, region)
);
