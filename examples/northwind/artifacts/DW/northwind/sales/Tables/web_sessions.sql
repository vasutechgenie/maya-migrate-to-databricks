CREATE TABLE sales.web_sessions (
    session_key   BIGINT     NOT NULL,
    customer_key  BIGINT     NULL,
    session_start DATETIME2  NULL,
    session_end   DATETIME2  NULL,
    page_views    INT        NULL,
    load_dt       DATETIME2  NULL,
    CONSTRAINT PK_web_sessions PRIMARY KEY (session_key)
);
