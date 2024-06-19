with tab_v2v as (
    select mitra_id,
    CASE WHEN UPPER(cluster) = "PRIANGAN TIMUR 1" THEN "PRIANGAN TIMUR"
    WHEN UPPER(cluster) = "PRIANGAN TIMUR 2" THEN "PRIANGAN TIMUR"
    ELSE UPPER(cluster) END cluster
    from mp_bi.mp_bi_fact_mitra_v2v 
) 

select v2v.mitra_id, v2v.cluster 
from tab_v2v v2v
left join mp_mst.mp_mst_mitra_details mmmd on mmmd.mitra_id = v2v.mitra_id
where cluster = UPPER("{cluster_name}") and date(mmmd.created_at) <= "{snapshot_dt}"
order by 1