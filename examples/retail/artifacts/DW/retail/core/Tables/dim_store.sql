CREATE TABLE core.dim_store (
    store_key  BIGINT       NOT NULL,
    store_id   BIGINT       NOT NULL,
    store_name VARCHAR(160) NULL,
    region     VARCHAR(64)  NULL,
    city       VARCHAR(120) NULL,
    load_dt    TIMESTAMP    NULL,
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key)
);
