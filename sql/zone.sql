, pd as (select m, count(distinct d) days from tk group by 1),
a as (select m period, zone, count(*) tickets, round(avg(rs),4) res_pct, round(avg(iff(rmin<=240,1,0)),4) le4_pct, round(avg(iff(rmin<=720,1,0)),4) le12_pct, round(avg(iff(rmin<=1440,1,0)),4) le24_pct, round(avg(iff(rmin<=2880,1,0)),4) le48_pct, round(avg(iff(rmin<=4320,1,0)),4) le72_pct, round(avg(iff(rmin>4320,1,0)),4) gt72_pct, round(1-avg(rs),4) open_pct, sum(ro) reopened, round(sum(ro)/nullif(sum(rs),0),4) reopen_pct, round(avg(rmin)/60,1) avg_res_hrs, round(avg(rp),4) repeat7_pct
  from tk group by 1,2)
select a.*, round(a.tickets/pd.days,1) per_day,
 round((a.tickets/pd.days)/nullif(lag(a.tickets/pd.days) over (partition by zone order by period),0)-1,4) per_day_chg_pct
from a join pd on pd.m=a.period order by period, tickets desc
