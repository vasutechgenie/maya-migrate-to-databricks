CREATE TABLE src.products (
    product_id   BIGINT       NOT NULL,
    product_name VARCHAR(200) NULL,
    category     VARCHAR(64)  NULL,
    supplier_id  BIGINT       NULL,
    unit_price   DECIMAL(18,2) NULL,
    load_dt      DATETIME2    NULL
);
