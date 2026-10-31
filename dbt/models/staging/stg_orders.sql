with source as (
    select
        order_id,
        customer_id,
        lower(trim(order_status)) as order_status,
        cast(order_purchase_timestamp as timestamp) as order_purchase_timestamp,
        cast(order_approved_at as timestamp) as order_approved_at,
        cast(order_delivered_customer_date as timestamp) as order_delivered_customer_date,
        cast(order_estimated_delivery_date as timestamp) as order_estimated_delivery_date
    from {{ source('raw_ecommerce', 'orders') }}
),
deduplicated as (
    select
        *,
        row_number() over (
            partition by order_id
            order by order_purchase_timestamp desc nulls last
        ) as row_number
    from source
)
select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_customer_date,
    order_estimated_delivery_date
from deduplicated
where row_number = 1
