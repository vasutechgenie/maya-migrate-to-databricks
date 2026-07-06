-- MAYA live-demo source system: a compact, deterministic Northwind in PostgreSQL.
-- This is the REAL source that MAYA migrates to Databricks. It contains tables with
-- referential integrity, views, a stored function (the "pipeline"), and a gold mart the
-- function builds. All data is generated deterministically so parity is reproducible.
--
-- Idempotent: safe to re-run (drops + recreates the maya_src / maya_gold schemas).

DROP SCHEMA IF EXISTS maya_gold CASCADE;
DROP SCHEMA IF EXISTS maya_src CASCADE;
CREATE SCHEMA maya_src;
CREATE SCHEMA maya_gold;

SET search_path = maya_src, public;

-- ---------------------------------------------------------------------------
-- dimensions
-- ---------------------------------------------------------------------------
CREATE TABLE maya_src.categories (
    category_id   INT PRIMARY KEY,
    category_name VARCHAR(64) NOT NULL
);

CREATE TABLE maya_src.suppliers (
    supplier_id  INT PRIMARY KEY,
    company_name VARCHAR(96) NOT NULL,
    country      VARCHAR(48) NOT NULL
);

CREATE TABLE maya_src.products (
    product_id   INT PRIMARY KEY,
    product_name VARCHAR(96) NOT NULL,
    supplier_id  INT NOT NULL REFERENCES maya_src.suppliers(supplier_id),
    category_id  INT NOT NULL REFERENCES maya_src.categories(category_id),
    unit_price   NUMERIC(10,2) NOT NULL,
    discontinued BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE maya_src.customers (
    customer_id  INT PRIMARY KEY,
    company_name VARCHAR(96) NOT NULL,
    country      VARCHAR(48) NOT NULL,
    city         VARCHAR(48) NOT NULL
);

CREATE TABLE maya_src.employees (
    employee_id INT PRIMARY KEY,
    last_name   VARCHAR(48) NOT NULL,
    first_name  VARCHAR(48) NOT NULL,
    title       VARCHAR(48) NOT NULL
);

CREATE TABLE maya_src.shippers (
    shipper_id   INT PRIMARY KEY,
    company_name VARCHAR(64) NOT NULL
);

-- ---------------------------------------------------------------------------
-- facts
-- ---------------------------------------------------------------------------
CREATE TABLE maya_src.orders (
    order_id    INT PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES maya_src.customers(customer_id),
    employee_id INT NOT NULL REFERENCES maya_src.employees(employee_id),
    shipper_id  INT NOT NULL REFERENCES maya_src.shippers(shipper_id),
    order_date  DATE NOT NULL
);

CREATE TABLE maya_src.order_details (
    order_id   INT NOT NULL REFERENCES maya_src.orders(order_id),
    product_id INT NOT NULL REFERENCES maya_src.products(product_id),
    unit_price NUMERIC(10,2) NOT NULL,
    quantity   INT NOT NULL,
    discount   NUMERIC(4,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, product_id)
);

-- ---------------------------------------------------------------------------
-- deterministic data (referential integrity via modulo mapping to parents)
-- ---------------------------------------------------------------------------
INSERT INTO maya_src.categories (category_id, category_name)
SELECT g, (ARRAY['Beverages','Condiments','Confections','Dairy','Grains',
                 'Meat','Produce','Seafood'])[g]
FROM generate_series(1, 8) g;

INSERT INTO maya_src.suppliers (supplier_id, company_name, country)
SELECT g, 'Supplier ' || g,
       (ARRAY['USA','UK','Germany','France','Japan','Brazil','Canada','Italy'])[1 + (g % 8)]
FROM generate_series(1, 20) g;

INSERT INTO maya_src.products (product_id, product_name, supplier_id, category_id,
                              unit_price, discontinued)
SELECT g, 'Product ' || g,
       1 + (g % 20),
       1 + (g % 8),
       ROUND((5 + (g % 50) * 1.5)::numeric, 2),
       (g % 17 = 0)
FROM generate_series(1, 77) g;

INSERT INTO maya_src.customers (customer_id, company_name, country, city)
SELECT g, 'Customer ' || g,
       (ARRAY['USA','UK','Germany','France','Japan','Brazil','Canada','Italy',
              'Spain','Mexico'])[1 + (g % 10)],
       'City ' || (1 + (g % 25))
FROM generate_series(1, 91) g;

INSERT INTO maya_src.employees (employee_id, last_name, first_name, title)
SELECT g, 'Last' || g, 'First' || g,
       (ARRAY['Sales Rep','Sales Manager','VP Sales'])[1 + (g % 3)]
FROM generate_series(1, 9) g;

INSERT INTO maya_src.shippers (shipper_id, company_name)
SELECT g, (ARRAY['Speedy Express','United Package','Federal Shipping'])[g]
FROM generate_series(1, 3) g;

INSERT INTO maya_src.orders (order_id, customer_id, employee_id, shipper_id, order_date)
SELECT g,
       1 + (g % 91),
       1 + (g % 9),
       1 + (g % 3),
       DATE '2023-01-01' + ((g * 7) % 700)
FROM generate_series(1, 830) g;

INSERT INTO maya_src.order_details (order_id, product_id, unit_price, quantity, discount)
SELECT t.order_id, t.product_id, p.unit_price, t.quantity,
       CASE WHEN t.order_id % 5 = 0 THEN 0.10 ELSE 0.00 END
FROM (
    SELECT o.order_id,
           ((o.order_id + j * 13) % 77) + 1 AS product_id,
           1 + ((o.order_id + j) % 5)       AS quantity
    FROM maya_src.orders o
    CROSS JOIN LATERAL generate_series(0, o.order_id % 4) AS g(j)
) t
JOIN maya_src.products p ON p.product_id = t.product_id
ON CONFLICT (order_id, product_id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- views
-- ---------------------------------------------------------------------------
CREATE VIEW maya_src.v_order_totals AS
SELECT od.order_id,
       SUM(od.unit_price * od.quantity * (1 - od.discount)) AS order_total,
       SUM(od.quantity)                                     AS units
FROM maya_src.order_details od
GROUP BY od.order_id;

CREATE VIEW maya_src.v_product_catalog AS
SELECT p.product_id, p.product_name, c.category_name, s.company_name AS supplier,
       p.unit_price, p.discontinued
FROM maya_src.products p
JOIN maya_src.categories c ON c.category_id = p.category_id
JOIN maya_src.suppliers  s ON s.supplier_id = p.supplier_id;

-- ---------------------------------------------------------------------------
-- the "pipeline": a stored function that (re)builds the gold sales mart.
-- MAYA reads this transformation logic and re-authors it as a Databricks pipeline;
-- parity compares the Databricks-built mart against this function's output.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION maya_gold.refresh_mart_sales_daily()
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    DROP TABLE IF EXISTS maya_gold.mart_sales_daily;
    CREATE TABLE maya_gold.mart_sales_daily AS
    SELECT o.order_date,
           c.category_name,
           COUNT(DISTINCT o.order_id)                              AS orders,
           SUM(od.quantity)                                        AS units,
           ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount)), 2) AS revenue
    FROM maya_src.orders o
    JOIN maya_src.order_details od ON od.order_id = o.order_id
    JOIN maya_src.products p       ON p.product_id = od.product_id
    JOIN maya_src.categories c     ON c.category_id = p.category_id
    GROUP BY o.order_date, c.category_name;
END;
$$;

SELECT maya_gold.refresh_mart_sales_daily();
