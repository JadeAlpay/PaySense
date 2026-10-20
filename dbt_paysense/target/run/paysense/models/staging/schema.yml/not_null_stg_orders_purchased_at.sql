
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select purchased_at
from "paysense_analytics"."main"."stg_orders"
where purchased_at is null



  
  
      
    ) dbt_internal_test