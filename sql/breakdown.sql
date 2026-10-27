, x as (select tk.*, m period, 'month' ptype from tk
        union all select tk.*, m || '-' || wk, 'week' from tk where m = (select cur_m from params)),
pd as (select period, count(distinct d) days, min(day(d)) d0, max(day(d)) d1, min(d) dmin from x group by 1),
agg as (
  select ptype, period,
    iff(ptype = 'month',
        to_char(any_value(pd.dmin),'Mon') || iff(period = (select cur_m from params), ' MTD', ''),
        to_char(any_value(pd.dmin),'Mon') || ' ' || right(period, 2) || ' (' || any_value(pd.d0) || '–' || any_value(pd.d1) || ')') period_label,
    any_value(pd.days) days, (select to_char(max(ts),'YYYY-MM-DD HH24:MI') from tk) asof, cat, cs, q, ws, ch,
    count(*) tickets, sum(rs) resolved,
    sum(iff(rmin<=240,1,0)) n4, sum(iff(rmin<=720,1,0)) n12, sum(iff(rmin<=1440,1,0)) n24, sum(iff(rmin<=2880,1,0)) n48, sum(iff(rmin<=4320,1,0)) n72, sum(iff(rmin>4320,1,0)) n72p,
    sum(ro) reopened, count(rmin) res_timed, round(sum(rmin)) res_mins, sum(rp) repeat7
  from x join pd using(period)
  group by ptype, period, cat, cs, q, ws, ch
),
-- Resolution-time histogram per cell, so the page can merge cells and read percentiles (P50/P90/P95).
-- Bucket: 15-min steps below 24h (0–95), 1-hour steps to 7 days (96–239), 1-day steps beyond (240–419, capped at ~187 days).
hb as (
  select ptype, period, cat, cs, q,
    case when rmin < 1440 then floor(greatest(rmin,0)/15)
         when rmin < 10080 then 96 + floor((rmin-1440)/60)
         else 240 + least(floor((rmin-10080)/1440), 179) end bkt,
    count(*) n
  from x where rmin is not null group by 1,2,3,4,5,6
),
hl as (select ptype, period, cat, cs, q, listagg(bkt || ':' || n, ',') within group (order by bkt) hist from hb group by 1,2,3,4,5)
select agg.*, hl.hist from agg left join hl using(ptype, period, cat, cs, q)
order by ptype, period, tickets desc
