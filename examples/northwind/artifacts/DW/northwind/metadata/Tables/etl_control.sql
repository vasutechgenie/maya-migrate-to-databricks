CREATE TABLE metadata.etl_control (
    table_name      VARCHAR(128) NOT NULL,
    watermark_col   VARCHAR(64)  NOT NULL,
    watermark_value DATETIME2    NULL,
    last_run_ts     DATETIME2    NULL,
    status          VARCHAR(16)  NULL,
    CONSTRAINT PK_etl_control PRIMARY KEY (table_name)
);
