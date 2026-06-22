-- E-commerce Analytics Queries for Amazon Athena
-- Brazilian E-commerce Dataset Analysis
-- Database: etl_catalog

-- Query 1: Monthly Revenue Trend with Year-over-Year Comparison
-- Purpose: Track revenue growth and identify seasonal patterns
SELECT 
    o.order_year,
    o.order_month,
    DATE_TRUNC('month', o.order_purchase_timestamp) as month_date,
    COUNT(DISTINCT o.order_id) as total_orders,
    COUNT(DISTINCT o.customer_id) as unique_customers,
    SUM(oi.total_value) as monthly_revenue,
    AVG(oi.total_value) as avg_order_value,
    SUM(oi.total_value) - LAG(SUM(oi.total_value), 12) OVER (ORDER BY o.order_year, o.order_month) as yoy_revenue_change,
    ROUND(
        (SUM(oi.total_value) - LAG(SUM(oi.total_value), 12) OVER (ORDER BY o.order_year, o.order_month)) 
        / NULLIF(LAG(SUM(oi.total_value), 12) OVER (ORDER BY o.order_year, o.order_month), 0) * 100,
        2
    ) as yoy_growth_pct
FROM 
    etl_catalog.fact_orders o
    INNER JOIN etl_catalog.fact_order_items oi ON o.order_id = oi.order_id
WHERE 
    o.order_status = 'delivered'
GROUP BY 
    o.order_year, o.order_month, DATE_TRUNC('month', o.order_purchase_timestamp)
ORDER BY 
    o.order_year DESC, o.order_month DESC
LIMIT 24;


-- Query 2: Top Performing Product Categories by Revenue and Margin
-- Purpose: Identify most profitable product categories
SELECT 
    p.product_category_name_english as category,
    COUNT(DISTINCT oi.order_id) as total_orders,
    SUM(oi.price) as total_product_revenue,
    SUM(oi.freight_value) as total_freight_revenue,
    SUM(oi.total_value) as total_revenue,
    AVG(oi.price) as avg_product_price,
    AVG(oi.freight_value) as avg_freight_cost,
    ROUND(SUM(oi.freight_value) / NULLIF(SUM(oi.price), 0) * 100, 2) as freight_to_price_ratio,
    SUM(oi.total_value) / NULLIF(COUNT(DISTINCT oi.order_id), 0) as revenue_per_order,
    PERCENT_RANK() OVER (ORDER BY SUM(oi.total_value) DESC) as revenue_percentile
FROM 
    etl_catalog.fact_order_items oi
    INNER JOIN etl_catalog.dim_products p ON oi.product_id = p.product_id
    INNER JOIN etl_catalog.fact_orders o ON oi.order_id = o.order_id
WHERE 
    o.order_status = 'delivered'
    AND p.product_category_name_english IS NOT NULL
GROUP BY 
    p.product_category_name_english
HAVING 
    COUNT(DISTINCT oi.order_id) >= 100
ORDER BY 
    total_revenue DESC
LIMIT 20;


-- Query 3: Customer Segmentation by Purchase Behavior (RFM Analysis)
-- Purpose: Segment customers for targeted marketing campaigns
WITH customer_metrics AS (
    SELECT 
        c.customer_id,
        c.customer_state,
        c.customer_city,
        MAX(o.order_purchase_timestamp) as last_purchase_date,
        DATE_DIFF('day', MAX(o.order_purchase_timestamp), CURRENT_TIMESTAMP) as recency_days,
        COUNT(DISTINCT o.order_id) as frequency,
        SUM(oi.total_value) as monetary_value,
        AVG(oi.total_value) as avg_order_value
    FROM 
        etl_catalog.dim_customers c
        INNER JOIN etl_catalog.fact_orders o ON c.customer_id = o.customer_id
        INNER JOIN etl_catalog.fact_order_items oi ON o.order_id = oi.order_id
    WHERE 
        o.order_status = 'delivered'
    GROUP BY 
        c.customer_id, c.customer_state, c.customer_city
),
rfm_scores AS (
    SELECT 
        *,
        NTILE(5) OVER (ORDER BY recency_days ASC) as r_score,
        NTILE(5) OVER (ORDER BY frequency DESC) as f_score,
        NTILE(5) OVER (ORDER BY monetary_value DESC) as m_score
    FROM customer_metrics
)
SELECT 
    CASE 
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Potential Loyalists'
        WHEN r_score >= 3 AND m_score >= 3 THEN 'Big Spenders'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost Customers'
        ELSE 'Regular Customers'
    END as customer_segment,
    COUNT(DISTINCT customer_id) as customer_count,
    ROUND(AVG(recency_days), 0) as avg_recency_days,
    ROUND(AVG(frequency), 2) as avg_frequency,
    ROUND(AVG(monetary_value), 2) as avg_monetary_value,
    ROUND(AVG(avg_order_value), 2) as avg_order_value,
    ROUND(SUM(monetary_value), 2) as total_segment_value,
    ROUND(SUM(monetary_value) * 100.0 / SUM(SUM(monetary_value)) OVER(), 2) as pct_of_total_revenue
FROM rfm_scores
GROUP BY 
    CASE 
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'Potential Loyalists'
        WHEN r_score >= 3 AND m_score >= 3 THEN 'Big Spenders'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost Customers'
        ELSE 'Regular Customers'
    END
ORDER BY total_segment_value DESC;


-- Query 4: Delivery Performance Analysis by State
-- Purpose: Identify delivery issues and optimize logistics
SELECT 
    c.customer_state,
    COUNT(DISTINCT o.order_id) as total_orders,
    COUNT(DISTINCT CASE WHEN o.is_delayed THEN o.order_id END) as delayed_orders,
    ROUND(
        COUNT(DISTINCT CASE WHEN o.is_delayed THEN o.order_id END) * 100.0 / 
        NULLIF(COUNT(DISTINCT o.order_id), 0),
        2
    ) as delay_rate_pct,
    ROUND(AVG(o.delivery_days), 1) as avg_delivery_days,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.delivery_days), 1) as median_delivery_days,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY o.delivery_days), 1) as p95_delivery_days,
    MIN(o.delivery_days) as min_delivery_days,
    MAX(o.delivery_days) as max_delivery_days,
    SUM(oi.total_value) as total_revenue,
    COUNT(DISTINCT c.customer_id) as unique_customers
FROM 
    etl_catalog.fact_orders o
    INNER JOIN etl_catalog.dim_customers c ON o.customer_id = c.customer_id
    INNER JOIN etl_catalog.fact_order_items oi ON o.order_id = oi.order_id
WHERE 
    o.order_status = 'delivered'
    AND o.order_delivered_customer_date IS NOT NULL
    AND o.delivery_days IS NOT NULL
GROUP BY 
    c.customer_state
HAVING 
    COUNT(DISTINCT o.order_id) >= 50
ORDER BY 
    total_revenue DESC
LIMIT 30;


-- Query 5: Seller Performance Ranking and Market Share
-- Purpose: Identify top sellers and marketplace concentration
WITH seller_performance AS (
    SELECT 
        s.seller_id,
        s.seller_city,
        s.seller_state,
        COUNT(DISTINCT oi.order_id) as total_orders,
        COUNT(DISTINCT o.customer_id) as unique_customers,
        SUM(oi.total_value) as total_revenue,
        SUM(oi.price) as product_revenue,
        SUM(oi.freight_value) as freight_revenue,
        AVG(oi.price) as avg_product_price,
        COUNT(DISTINCT p.product_id) as unique_products_sold,
        COUNT(DISTINCT p.product_category_name) as category_diversity,
        AVG(o.delivery_days) as avg_delivery_days,
        SUM(CASE WHEN o.is_delayed THEN 1 ELSE 0 END) * 100.0 / 
            NULLIF(COUNT(DISTINCT oi.order_id), 0) as delay_rate_pct
    FROM 
        etl_catalog.dim_sellers s
        INNER JOIN etl_catalog.fact_order_items oi ON s.seller_id = oi.seller_id
        INNER JOIN etl_catalog.fact_orders o ON oi.order_id = o.order_id
        INNER JOIN etl_catalog.dim_products p ON oi.product_id = p.product_id
    WHERE 
        o.order_status = 'delivered'
    GROUP BY 
        s.seller_id, s.seller_city, s.seller_state
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as seller_rank,
    seller_id,
    seller_city,
    seller_state,
    total_orders,
    unique_customers,
    ROUND(total_revenue, 2) as total_revenue,
    ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER(), 4) as market_share_pct,
    ROUND(SUM(total_revenue) OVER (ORDER BY total_revenue DESC) * 100.0 / SUM(total_revenue) OVER(), 2) as cumulative_market_share_pct,
    ROUND(avg_product_price, 2) as avg_product_price,
    unique_products_sold,
    category_diversity,
    ROUND(avg_delivery_days, 1) as avg_delivery_days,
    ROUND(delay_rate_pct, 2) as delay_rate_pct,
    ROUND(total_revenue / NULLIF(total_orders, 0), 2) as revenue_per_order,
    ROUND(total_revenue / NULLIF(unique_customers, 0), 2) as revenue_per_customer
FROM 
    seller_performance
WHERE 
    total_orders >= 10
ORDER BY 
    total_revenue DESC
LIMIT 100;
