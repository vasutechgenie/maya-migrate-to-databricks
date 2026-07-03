CREATE TABLE sales.dim_customer (
    customer_key   BIGINT       NOT NULL,
    customer_id    BIGINT       NOT NULL,
    customer_name  VARCHAR(200) NULL,
    region         VARCHAR(64)  NULL,
    segment        VARCHAR(32)  NULL,
    is_active      BIT          NULL,
    effective_from DATE         NULL,
    effective_to   DATE         NULL,
    load_dt        DATETIME2    NULL,
    CONSTRAINT PK_dim_customer PRIMARY KEY (customer_key)
);
