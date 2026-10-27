-- Daily alert numbers, each compared on equally old tickets so recent days aren't penalised for being young.
--   Tickets:          created yesterday (D-1)            vs D-8
--   Resolved <=24h:   created D-2 (24h fully elapsed)     vs D-9
--   Reopen <=48h:     created D-10..D-4, first resolved >=48h ago, reopened within 48h of that resolution  vs D-17..D-11
--   P95 (cap 72h):    created D-10..D-4 (all >=72h old), resolution time with open = 72h+               vs D-17..D-11
, p as (select (select now_ist from params)::date today),
c as (select tk.*, datediff(day, d, (select today from p)) age_d from tk where d >= dateadd(day, -17, (select today from p))),
dims as (
  select 'All tickets' dim, 'All tickets' val, c.* from c
  union all select 'Workstream', ws, c.* from c
  union all select 'Chat / call', ch, c.* from c
  union all select 'Category', cat, c.* from c
  union all select 'Sub-category', cs, c.* from c
  union all select 'Queue', q, c.* from c
  union all select 'Workstream › category', ws || ' › ' || cat, c.* from c
)
select dim, val,
  to_char(dateadd(day, -1, (select today from p)), 'YYYY-MM-DD') d_vol_cur, to_char(dateadd(day, -8, (select today from p)), 'YYYY-MM-DD') d_vol_prev,
  to_char(dateadd(day, -2, (select today from p)), 'YYYY-MM-DD') d_r24_cur, to_char(dateadd(day, -9, (select today from p)), 'YYYY-MM-DD') d_r24_prev,
  count_if(age_d = 1) vol_cur, count_if(age_d = 8) vol_prev,
  count_if(age_d = 2) r24_base_cur, count_if(age_d = 2 and rmin <= 1440) r24_cur,
  count_if(age_d = 9) r24_base_prev, count_if(age_d = 9 and rmin <= 1440) r24_prev,
  count_if(age_d between 4 and 10 and frt <= dateadd(hour, -48, sysdate())) ro_base_cur,
  count_if(age_d between 4 and 10 and frt <= dateadd(hour, -48, sysdate()) and fro is not null and fro > frt and fro <= dateadd(hour, 48, frt)) ro_cur,
  count_if(age_d between 11 and 17 and frt <= dateadd(hour, -48, sysdate())) ro_base_prev,
  count_if(age_d between 11 and 17 and frt <= dateadd(hour, -48, sysdate()) and fro is not null and fro > frt and fro <= dateadd(hour, 48, frt)) ro_prev,
  count_if(age_d between 4 and 10) p95_base_cur,
  round(percentile_cont(0.95) within group (order by iff(age_d between 4 and 10, least(coalesce(rmin, 4320), 4320), null)) / 60, 1) p95_cur,
  count_if(age_d between 11 and 17) p95_base_prev,
  round(percentile_cont(0.95) within group (order by iff(age_d between 11 and 17, least(coalesce(rmin, 4320), 4320), null)) / 60, 1) p95_prev
from dims group by 1, 2
