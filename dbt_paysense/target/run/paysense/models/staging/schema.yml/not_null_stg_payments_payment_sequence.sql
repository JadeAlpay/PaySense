
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select payment_sequence
from "paysense_analytics"."main"."stg_payments"
where payment_sequence is null



  
  
      
    ) dbt_internal_test