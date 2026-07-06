CREATE TABLE core.dim_date (
    date_key    INT     NOT NULL,
    cal_date    DATE    NOT NULL,
    day_of_week INT     NULL,
    month       INT     NULL,
    quarter     INT     NULL,
    year        INT     NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);
