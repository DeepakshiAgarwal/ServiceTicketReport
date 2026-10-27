, pdays as (select m, count(distinct d) days from tk group by 1),
cur as (select pid::text partner_id, any_value(pname) partner, mode(zone) zone, count(*) tickets, round(avg(rs),4) res_pct, round(avg(iff(rmin<=240,1,0)),4) le4_pct, round(avg(iff(rmin<=720,1,0)),4) le12_pct, round(avg(iff(rmin<=1440,1,0)),4) le24_pct, round(avg(iff(rmin<=2880,1,0)),4) le48_pct, round(avg(iff(rmin<=4320,1,0)),4) le72_pct, round(avg(iff(rmin>4320,1,0)),4) gt72_pct, round(1-avg(rs),4) open_pct, sum(ro) reopened, round(sum(ro)/nullif(sum(rs),0),4) reopen_pct, round(avg(rmin)/60,1) avg_res_hrs, round(avg(rp),4) repeat7_pct
  from tk where m = (select cur_m from params) and pid is not null group by 1),
prev as (select pid::text partner_id, count(*) / any_value(pdays.days) prev_per_day from tk join pdays using(m) where m = (select prev_m from params) and pid is not null group by 1),
cd as (select days from pdays where m = (select cur_m from params))
select cur.*, round(cur.tickets/(select days from cd),1) per_day, round((cur.tickets/(select days from cd))/nullif(prev.prev_per_day,0)-1,4) per_day_chg_pct
from cur left join prev using(partner_id) order by tickets desc limit 50
