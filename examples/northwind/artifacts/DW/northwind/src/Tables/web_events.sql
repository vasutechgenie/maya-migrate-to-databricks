CREATE TABLE src.web_events (
    event_id    BIGINT       NOT NULL,
    customer_id BIGINT       NULL,
    event_ts    DATETIME2    NULL,
    url         VARCHAR(512) NULL,
    event_type  VARCHAR(32)  NULL,
    load_dt     DATETIME2    NULL
);
