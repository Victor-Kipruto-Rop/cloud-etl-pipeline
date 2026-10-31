select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    case
        when order_delivered_customer_date is not null
         and order_estimated_delivery_date is not null
        then order_delivered_customer_date > order_estimated_delivery_date
        else false
    end as is_delayed,
    current_timestamp as dbt_loaded_at
from {{ ref('stg_orders') }}
