-- MAYA live-demo source system: a compact, deterministic Retail estate in PostgreSQL.
-- This is a REAL source that MAYA migrates to Databricks. It contains referential-
-- integrity tables, views, PL/pgSQL "job" functions that build gold marts, an in-DB
-- job/control table pair (retail_meta.etl_jobs / etl_control), and deterministic data
-- (~10k sale lines) so parity is reproducible.
--
-- Idempotent: safe to re-run (drops + recreates the retail_src / retail_gold / retail_meta
-- schemas).

DROP SCHEMA IF EXISTS retail_gold CASCADE;
DROP SCHEMA IF EXISTS retail_meta CASCADE;
DROP SCHEMA IF EXISTS retail_src CASCADE;
CREATE SCHEMA retail_src;
CREATE SCHEMA retail_gold;
CREATE SCHEMA retail_meta;

SET search_path = retail_src, public;

-- ---------------------------------------------------------------------------
-- dimensions / masters
-- ---------------------------------------------------------------------------
CREATE TABLE retail_src.customers (
    customer_id   INT PRIMARY KEY,
    customer_name VARCHAR(200) NOT NULL,
    email         VARCHAR(200) NOT NULL,
    phone         VARCHAR(40)  NOT NULL,
    city          VARCHAR(120) NOT NULL,
    region        VARCHAR(64)  NOT NULL,
    segment       VARCHAR(32)  NOT NULL
);

CREATE TABLE retail_src.products (
    product_id   INT PRIMARY KEY,
    product_name VARCHAR(200)  NOT NULL,
    category     VARCHAR(80)   NOT NULL,
    brand        VARCHAR(80)   NOT NULL,
    unit_price   NUMERIC(12,2) NOT NULL
);

CREATE TABLE retail_src.stores (
    store_id   INT PRIMARY KEY,
    store_name VARCHAR(160) NOT NULL,
    region     VARCHAR(64)  NOT NULL,
    city       VARCHAR(120) NOT NULL
);

-- ---------------------------------------------------------------------------
-- facts (POS)
-- ---------------------------------------------------------------------------
CREATE TABLE retail_src.sales (
    sale_id     INT PRIMARY KEY,
    store_id    INT NOT NULL REFERENCES retail_src.stores(store_id),
    customer_id INT NOT NULL REFERENCES retail_src.customers(customer_id),
    sale_ts     TIMESTAMP NOT NULL,
    channel     VARCHAR(24) NOT NULL
);

CREATE TABLE retail_src.sale_items (
    sale_id    INT NOT NULL REFERENCES retail_src.sales(sale_id),
    line_no    INT NOT NULL,
    product_id INT NOT NULL REFERENCES retail_src.products(product_id),
    qty        INT NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    discount   NUMERIC(4,2)  NOT NULL DEFAULT 0,
    PRIMARY KEY (sale_id, line_no)
);

-- e-commerce web orders (a separate source feed)
CREATE TABLE retail_src.web_orders (
    web_order_id INT PRIMARY KEY,
    customer_id  INT NOT NULL REFERENCES retail_src.customers(customer_id),
    product_id   INT NOT NULL REFERENCES retail_src.products(product_id),
    order_ts     TIMESTAMP NOT NULL,
    qty          INT NOT NULL,
    unit_price   NUMERIC(12,2) NOT NULL
);

-- ---------------------------------------------------------------------------
-- in-warehouse job + control tables (the "scheduler" lives in the DB)
-- ---------------------------------------------------------------------------
CREATE TABLE retail_meta.etl_control (
    table_name      VARCHAR(128) PRIMARY KEY,
    watermark_col   VARCHAR(64)  NOT NULL,
    watermark_value TIMESTAMP    NULL,
    last_run_ts     TIMESTAMP    NULL,
    status          VARCHAR(16)  NULL
);

CREATE TABLE retail_meta.etl_jobs (
    job_name        VARCHAR(64) PRIMARY KEY,
    schedule        VARCHAR(32) NOT NULL,
    target_pipeline VARCHAR(64) NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------------
-- deterministic data (referential integrity via modulo mapping to parents)
-- ---------------------------------------------------------------------------
INSERT INTO retail_src.customers (customer_id, customer_name, email, phone, city, region, segment)
SELECT g,
       'Customer ' || g,
       'customer' || g || '@example.com',
       '+1-555-' || lpad((g % 10000)::text, 4, '0'),
       'City ' || (1 + (g % 40)),
       (ARRAY['West','East','North','South','Central'])[1 + (g % 5)],
       (ARRAY['Consumer','SMB','Enterprise'])[1 + (g % 3)]
FROM generate_series(1, 500) g;

INSERT INTO retail_src.products (product_id, product_name, category, brand, unit_price)
SELECT g,
       'Product ' || g,
       (ARRAY['Grocery','Apparel','Electronics','Home','Toys','Sports','Beauty','Auto'])[1 + (g % 8)],
       'Brand ' || (1 + (g % 25)),
       ROUND((3 + (g % 120) * 1.25)::numeric, 2)
FROM generate_series(1, 200) g;

INSERT INTO retail_src.stores (store_id, store_name, region, city)
SELECT g,
       'Store ' || g,
       (ARRAY['West','East','North','South','Central'])[1 + (g % 5)],
       'City ' || (1 + (g % 40))
FROM generate_series(1, 25) g;

INSERT INTO retail_src.sales (sale_id, store_id, customer_id, sale_ts, channel)
SELECT g,
       1 + (g % 25),
       1 + (g % 500),
       TIMESTAMP '2024-01-01 08:00:00' + ((g % 365) * INTERVAL '1 day') + ((g % 12) * INTERVAL '1 hour'),
       (ARRAY['store','store','store','kiosk'])[1 + (g % 4)]
FROM generate_series(1, 4000) g;

-- ~10k sale lines: 1..4 items per sale, RI to products + sales
INSERT INTO retail_src.sale_items (sale_id, line_no, product_id, qty, unit_price, discount)
SELECT t.sale_id, t.line_no, t.product_id, t.qty, p.unit_price,
       CASE WHEN t.sale_id % 5 = 0 THEN 0.10 ELSE 0.00 END
FROM (
    SELECT s.sale_id,
           j + 1                                       AS line_no,
           ((s.sale_id + j * 7) % 200) + 1             AS product_id,
           1 + ((s.sale_id + j) % 6)                   AS qty
    FROM retail_src.sales s
    CROSS JOIN LATERAL generate_series(0, s.sale_id % 4) AS gen(j)
) t
JOIN retail_src.products p ON p.product_id = t.product_id
ON CONFLICT (sale_id, line_no) DO NOTHING;

INSERT INTO retail_src.web_orders (web_order_id, customer_id, product_id, order_ts, qty, unit_price)
SELECT g,
       1 + (g % 500),
       1 + (g % 200),
       TIMESTAMP '2024-01-01 00:00:00' + ((g % 365) * INTERVAL '1 day'),
       1 + (g % 4),
       ROUND((3 + (g % 120) * 1.25)::numeric, 2)
FROM generate_series(1, 3000) g;

INSERT INTO retail_meta.etl_control (table_name, watermark_col, watermark_value, last_run_ts, status)
VALUES
    ('stg.sales',      'sale_ts',  TIMESTAMP '2024-12-31 23:59:59', TIMESTAMP '2025-01-01 02:15:00', 'SUCCESS'),
    ('stg.sale_items', 'sale_ts',  TIMESTAMP '2024-12-31 23:59:59', TIMESTAMP '2025-01-01 02:16:00', 'SUCCESS'),
    ('stg.web_orders', 'order_ts', TIMESTAMP '2024-12-31 23:59:59', TIMESTAMP '2025-01-01 02:05:00', 'SUCCESS');

INSERT INTO retail_meta.etl_jobs (job_name, schedule, target_pipeline, enabled) VALUES
    ('job_rt_daily_master',    'DAILY', 'rt_daily_master',    TRUE),
    ('job_rt_ingest_pos',      'DAILY', 'rt_ingest_pos',      TRUE),
    ('job_rt_ingest_ecom',     'DAILY', 'rt_ingest_ecom',     TRUE),
    ('job_rt_loyalty_sync',    'DAILY', 'rt_loyalty_sync',    TRUE),
    ('job_rt_build_core',      'DAILY', 'rt_build_core',      TRUE),
    ('job_rt_build_web',       'DAILY', 'rt_build_web',       TRUE),
    ('job_rt_build_marts',     'DAILY', 'rt_build_marts',     TRUE),
    ('job_rt_publish_serving', 'DAILY', 'rt_publish_serving', TRUE);

-- ---------------------------------------------------------------------------
-- views
-- ---------------------------------------------------------------------------
CREATE VIEW retail_src.v_active_customers AS
SELECT c.customer_id, c.customer_name, c.region, c.segment
FROM retail_src.customers c
WHERE EXISTS (SELECT 1 FROM retail_src.sales s WHERE s.customer_id = c.customer_id);

CREATE VIEW retail_src.v_sale_totals AS
SELECT si.sale_id,
       SUM(si.unit_price * si.qty * (1 - si.discount)) AS net_amount,
       SUM(si.qty)                                     AS units
FROM retail_src.sale_items si
GROUP BY si.sale_id;

-- ---------------------------------------------------------------------------
-- the "pipelines": PL/pgSQL job functions that build the gold marts.
-- MAYA reads this transformation logic and re-authors it as Databricks pipelines;
-- parity compares the Databricks-built marts against these functions' output.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION retail_gold.refresh_sales_by_day()
RETURNS void LANGUAGE plpgsql AS $BODY$
BEGIN
    DROP TABLE IF EXISTS retail_gold.mart_sales_by_day;
    CREATE TABLE retail_gold.mart_sales_by_day AS
    SELECT CAST(s.sale_ts AS DATE) AS cal_date,
           st.region,
           COUNT(DISTINCT s.sale_id)                                        AS order_count,
           ROUND(SUM(si.unit_price * si.qty), 2)                            AS gross_amount,
           ROUND(SUM(si.unit_price * si.qty * si.discount), 2)             AS discount_amount,
           ROUND(SUM(si.unit_price * si.qty * (1 - si.discount)), 2)        AS net_amount
    FROM retail_src.sales s
    JOIN retail_src.sale_items si ON si.sale_id = s.sale_id
    JOIN retail_src.stores st     ON st.store_id = s.store_id
    GROUP BY CAST(s.sale_ts AS DATE), st.region;
END;
$BODY$;

CREATE OR REPLACE FUNCTION retail_gold.refresh_customer_360()
RETURNS void LANGUAGE plpgsql AS $BODY$
BEGIN
    DROP TABLE IF EXISTS retail_gold.mart_customer_360;
    CREATE TABLE retail_gold.mart_customer_360 AS
    SELECT c.customer_id,
           c.customer_name,
           c.region,
           c.segment,
           COUNT(DISTINCT s.sale_id)                                 AS orders_count,
           ROUND(COALESCE(SUM(si.unit_price * si.qty * (1 - si.discount)), 0), 2) AS lifetime_net,
           MAX(CAST(s.sale_ts AS DATE))                              AS last_order_date
    FROM retail_src.customers c
    LEFT JOIN retail_src.sales s      ON s.customer_id = c.customer_id
    LEFT JOIN retail_src.sale_items si ON si.sale_id = s.sale_id
    GROUP BY c.customer_id, c.customer_name, c.region, c.segment;
END;
$BODY$;

CREATE OR REPLACE FUNCTION retail_gold.refresh_product_perf()
RETURNS void LANGUAGE plpgsql AS $BODY$
BEGIN
    DROP TABLE IF EXISTS retail_gold.mart_product_perf;
    CREATE TABLE retail_gold.mart_product_perf AS
    SELECT p.product_id,
           p.product_name,
           p.category,
           SUM(si.qty)                                              AS units_sold,
           ROUND(SUM(si.unit_price * si.qty * (1 - si.discount)), 2) AS net_amount
    FROM retail_src.products p
    JOIN retail_src.sale_items si ON si.product_id = p.product_id
    GROUP BY p.product_id, p.product_name, p.category;
END;
$BODY$;

SELECT retail_gold.refresh_sales_by_day();
SELECT retail_gold.refresh_customer_360();
SELECT retail_gold.refresh_product_perf();
