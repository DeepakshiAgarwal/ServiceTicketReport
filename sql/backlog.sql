, o as (select cat, q, ws, ch, datediff('hour', ts, (select now_ist from params)) h from tk where rs=0)
select cat, q, ws, ch,
  case when h<=24 then '0–24h' when h<=48 then '24–48h' when h<=72 then '48–72h' when h<=168 then '3–7d' when h<=720 then '7–30d' else '30d+' end age_bucket,
  case when h<=24 then 1 when h<=48 then 2 when h<=72 then 3 when h<=168 then 4 when h<=720 then 5 else 6 end age_order,
  count(*) tickets
from o group by 1,2,3,4,5,6 order by 1,2,3,4,6
