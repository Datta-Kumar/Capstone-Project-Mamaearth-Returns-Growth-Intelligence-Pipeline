-- 3(a) Orders totals
-- Actual output: 180 | 99860.20 | 554.78

SELECT COUNT(*) AS total_orders,
	   ROUND(SUM(o.quantity * p.price *( 1 - COALESCE(o.discount_pct,0)/100 )),2) AS total_revenue,
       ROUND(AVG( o.quantity * p.price *( 1 - COALESCE(o.discount_pct,0)/100 )),2) AS avg_order_value
FROM orders o
LEFT JOIN products p
ON o.product_id = p.product_id;



-- 3(b) COUNT(*) vs COUNT(column)
-- Actual output: 180 | 165 | 15
-- 15 orders have no rating yet.

SELECT COUNT(*) AS total_orders,
       COUNT(rating) AS rated_orders,
       COUNT(*) - COUNT(rating) AS unrated_orders
FROM orders;



-- 3(c) LEFT JOIN with a genuine zero-match row
-- Query 1 output: C045 | Vihaan

SELECT c.customer_id, 
       c.name
FROM customers c
LEFT JOIN orders o
on c.customer_id = o.customer_id
GROUP BY c.customer_id
HAVING COUNT(o.order_id) = 0;

-- Query 2 output: C045 | Vihaan

SELECT customer_id,
       name
FROM customers
WHERE customer_id NOT IN (
				  SELECT DISTINCT customer_id 
                  FROM orders
                  );



-- 3(d) GROUP BY + HAVING
-- Actual output:
-- Jaipur | 19 | 8 | 42.1
-- Lucknow | 49 | 15 | 30.6
-- Bangalore | 33 | 8 | 24.2

SELECT c.city,
       COUNT(o.order_id) AS total_orders,
       SUM(CASE WHEN o.returned = 1 THEN 1 ELSE 0 END) AS returned_orders,
       ROUND(SUM(CASE WHEN o.returned = 1 THEN 1 ELSE 0 END)/COUNT(o.order_id) * 100,1) AS return_rate_pct
FROM orders o
LEFT JOIN customers c
on o.customer_id = c.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;



-- 3(e) Ranking customers by total spend
-- Actual output - LIMIT 5:
-- C043 | Reyansh | 12920.00
-- C026 | Isha    | 8371.60
-- C008 | Meera   | 4564.60
-- C011 | Arjun   | 4111.00
-- C042 | Sanya   | 3785.00
-- customer_id ASC provides a consistent order when customers have the same total_spend.

SELECT c.customer_id,
       c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct,0)/100)),2) AS total_spend
FROM orders o 
JOIN customers c
ON o.customer_id = c.customer_id
JOIN products p
ON o.product_id = p.product_id
GROUP BY c.customer_id,c.name
ORDER BY total_spend DESC,c.customer_id ASC
LIMIT 5;

-- 3(e) Ranks 3–5 using LIMIT + OFFSET
-- Actual output - LIMIT 3 OFFSET 2:
-- C008 | Meera | 4564.60
-- C011 | Arjun | 4111.00
-- C042 | Sanya | 3785.00

SELECT c.customer_id,
       c.name,
       ROUND(SUM(quantity * price * (1 - COALESCE(discount_pct,0)/100)),2) AS total_spend
FROM orders o 
JOIN customers c
ON o.customer_id = c.customer_id
JOIN products p
ON o.product_id = p.product_id
GROUP BY c.customer_id,c.name
ORDER BY total_spend DESC,c.customer_id ASC
LIMIT 3
OFFSET 2;


-- 3(f) Three-table JOIN with GROUP BY
-- Actual output:
-- Haircare | 54 | 44956.10
-- Skincare | 60 | 27346.00
-- Babycare | 30 | 16805.00
-- PersonalCare | 36 | 10753.10

SELECT p.category,
       COUNT(o.order_id) AS order_count,
       ROUND(SUM(o.quantity * p.price * 
					 (1 - COALESCE(o.discount_pct,0)/100)),2) AS category_revenue
FROM orders o
JOIN customers c
ON o.customer_id = c.customer_id
JOIN products p
ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY category_revenue DESC;



-- 3(g) LIKE pattern match
-- Actual output:
-- C001 | Aarav
-- C003 | Aditi
-- C004 | Ananya
-- C011 | Arjun
-- C021 | Aryan
-- C030 | Anika
-- C031 | Aditya
-- C036 | Aisha
-- C041 | Ayaan
-- C044 | Aria

SELECT customer_id, name 
FROM customers
WHERE name like 'A%';



-- 3(h) DISTINCT
-- Actual output:
-- Ad
-- Organic
-- Referral
-- Social

SELECT DISTINCT(acquisition_source) AS result
FROM customers
ORDER BY result;



-- 3(i) ALTER TABLE + UPDATE with CASE
-- Actual output:
-- Gold | 28
-- Silver | 17

ALTER TABLE customers 
ADD COLUMN loyalty_tier VARCHAR(10);

UPDATE customers
SET loyalty_tier =
    CASE
        WHEN city_tier = 1
               THEN 'Gold'
               ELSE 'Silver'
        END;
    
SELECT loyalty_tier,COUNT(*)
FROM customers
GROUP BY loyalty_tier;