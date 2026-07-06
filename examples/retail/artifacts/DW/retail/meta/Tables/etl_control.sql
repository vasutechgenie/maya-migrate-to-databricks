CREATE TABLE meta.etl_control (
    table_name      VARCHAR(128) NOT NULL,
    watermark_col   VARCHAR(64)  NOT NULL,
    watermark_value TIMESTAMP    NULL,
    last_run_ts     TIMESTAMP    NULL,
    status          VARCHAR(16)  NULL,
    CONSTRAINT pk_etl_control PRIMARY KEY (table_name)
);
