CREATE TABLE stg.customers (
    customer_id   BIGINT       NOT NULL,
    customer_name VARCHAR(200) NULL,
    email         VARCHAR(200) NULL,
    phone         VARCHAR(40)  NULL,
    city          VARCHAR(120) NULL,
    region        VARCHAR(64)  NULL,
    segment       VARCHAR(32)  NULL,
    load_dt       TIMESTAMP    NULL,
    CONSTRAINT pk_stg_customers PRIMARY KEY (customer_id)
);
