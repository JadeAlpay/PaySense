
    
    

select
    order_id as unique_field,
    count(*) as n_records

from "paysense_analytics"."main"."int_order_payments"
where order_id is not null
group by order_id
having count(*) > 1


