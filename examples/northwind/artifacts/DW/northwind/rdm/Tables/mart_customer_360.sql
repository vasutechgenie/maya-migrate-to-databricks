CREATE TABLE rdm.mart_customer_360 (
    customer_key      BIGINT        NOT NULL,
    region            VARCHAR(64)   NULL,
    lifetime_orders   INT           NULL,
    lifetime_revenue  DECIMAL(18,2) NULL,
    last_order_date   DATE          NULL,
    avg_session_pages DECIMAL(9,2)  NULL,
    load_dt           DATETIME2     NULL,
    CONSTRAINT PK_mart_customer_360 PRIMARY KEY (customer_key)
);
