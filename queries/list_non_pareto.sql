
with tab_list_prd as (
select distinct psat.prd_id,
from mp_ref.mp_ref_pareto_sku_ae_ter psat
where psat.input_date = '{pareto_date}' and psat.cluster ='{cluster_name}'),

tab_v2v as (
    select mitra_id,
    CASE WHEN UPPER(cluster) = "PRIANGAN TIMUR 1" THEN "PRIANGAN TIMUR"
    WHEN UPPER(cluster) = "PRIANGAN TIMUR 2" THEN "PRIANGAN TIMUR"
    ELSE UPPER(cluster) END cluster
    from mp_bi.mp_bi_fact_mitra_v2v 
),

tab_calc as (
select mmmp.prd_id prd_id,count(distinct mmod.str_trx_id) count_trx
from mp_mst.mp_mst_master_products mmmp
left join mp_mst.mp_mst_order_details mmod on mmmp.prd_id = mmod.trx_prd_id and mmod.trx_status = "COMPLETED" and date(mmod.trx_completed_at) < "{END_TRX_PERIOD}" and date(mmod.trx_completed_at) >= "{START_TRX_PERIOD}"
left join tab_v2v cluster on cluster.mitra_id = mmod.mitra_id 
where cluster.cluster = UPPER('{cluster_name}') and mmmp.prd_id NOT IN (select * from tab_list_prd) and mmmp.deleted_at is null
group by 1
order by 2 desc) 

select mmmp.prd_id, tc.count_trx
from mp_mst.mp_mst_master_products mmmp 
left join tab_calc as tc on tc.prd_id = mmmp.prd_id
left join mp_mst.mp_mst_master_products_360 mmmpts on mmmpts.prd_id = mmmp.prd_id
where mmmp.deleted_at is null and mmmp.prd_id NOT IN (select * from tab_list_prd) and mmmpts.is_bndl is False
order by 2 desc
limit {N_prd}

