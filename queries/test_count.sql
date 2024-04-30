select cluster, count(distinct psat.prd_id) count_pareto_prd
from mp_ref.mp_ref_pareto_sku_ae_ter psat
where batch_id in (select max(batch_id) from mp_ref.mp_ref_pareto_sku_ae_ter)
group by 1