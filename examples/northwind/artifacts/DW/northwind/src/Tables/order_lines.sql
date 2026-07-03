CREATE TABLE src.order_lines (
    order_line_id BIGINT        NOT NULL,
    order_id      BIGINT        NULL,
    product_id    BIGINT        NULL,
    qty           INT           NULL,
    unit_price    DECIMAL(18,2) NULL,
    discount      DECIMAL(9,4)  NULL,
    load_dt       DATETIME2     NULL
);
