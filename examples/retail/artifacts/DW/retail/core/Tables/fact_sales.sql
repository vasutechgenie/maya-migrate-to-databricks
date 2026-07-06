CREATE TABLE core.fact_sales (
    sale_key        BIGINT        NOT NULL,
    sale_id         BIGINT        NOT NULL,
    line_no         INT           NOT NULL,
    date_key        INT           NULL,
    customer_key    BIGINT        NULL,
    product_key     BIGINT        NULL,
    store_key       BIGINT        NULL,
    qty             INT           NULL,
    gross_amount    NUMERIC(14,2) NULL,
    discount_amount NUMERIC(14,2) NULL,
    net_amount      NUMERIC(14,2) NULL,
    load_dt         TIMESTAMP     NULL,
    CONSTRAINT pk_fact_sales PRIMARY KEY (sale_key)
);
