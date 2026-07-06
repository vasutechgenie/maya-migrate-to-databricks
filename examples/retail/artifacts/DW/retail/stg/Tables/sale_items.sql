CREATE TABLE stg.sale_items (
    sale_id    BIGINT        NOT NULL,
    line_no    INT           NOT NULL,
    product_id BIGINT        NULL,
    qty        INT           NULL,
    unit_price NUMERIC(12,2) NULL,
    discount   NUMERIC(4,2)  NULL,
    load_dt    TIMESTAMP     NULL,
    CONSTRAINT pk_stg_sale_items PRIMARY KEY (sale_id, line_no)
);
