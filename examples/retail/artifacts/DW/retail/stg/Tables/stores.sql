CREATE TABLE stg.stores (
    store_id   BIGINT       NOT NULL,
    store_name VARCHAR(160) NULL,
    region     VARCHAR(64)  NULL,
    city       VARCHAR(120) NULL,
    load_dt    TIMESTAMP    NULL,
    CONSTRAINT pk_stg_stores PRIMARY KEY (store_id)
);
