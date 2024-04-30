with tab_list_prd as (
select distinct psat.prd_id,
from mp_ref.mp_ref_pareto_sku_ae_ter psat
where psat.input_date = '{pareto_date}' and psat.cluster ='{cluster_name}')

select tlp.prd_id, count(distinct psat.batch_id) appearance
from tab_list_prd tlp 
left join mp_ref.mp_ref_pareto_sku_ae_ter psat on psat.prd_id = tlp.prd_id
left join mp_mst.mp_mst_master_products mmmp on mmmp.prd_id = tlp.prd_id
left join mp_mst.mp_mst_master_products_360 mmmpts on mmmpts.prd_id = tlp.prd_id
where  psat.cluster = '{cluster_name}' and psat.input_date <= '{pareto_date}' and mmmp.deleted_at is null 
and mmmpts.is_bndl is False
group by 1
order by 2 desc

