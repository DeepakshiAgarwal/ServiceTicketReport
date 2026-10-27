-- One row per created day × category × sub-category × queue × workstream × chat/call, with the same additive
-- counts and resolution-time histogram as breakdown.sql, so the page can total any date range.
, g as (
  select d, cat, cs, q, ws, ch,
    count(*) tickets, sum(rs) resolved,
    sum(iff(rmin<=240,1,0)) n4, sum(iff(rmin<=720,1,0)) n12, sum(iff(rmin<=1440,1,0)) n24, sum(iff(rmin<=2880,1,0)) n48, sum(iff(rmin<=4320,1,0)) n72, sum(iff(rmin>4320,1,0)) n72p,
    sum(ro) reopened, count(rmin) res_timed, round(sum(rmin)) res_mins, sum(rp) repeat7
  from tk group by 1,2,3,4,5,6
),
hb as (
  select d, cat, cs, q, ws, ch,
    case when rmin < 1440 then floor(greatest(rmin,0)/15)
         when rmin < 10080 then 96 + floor((rmin-1440)/60)
         else 240 + least(floor((rmin-10080)/1440), 179) end bkt,
    count(*) n
  from tk where rmin is not null group by 1,2,3,4,5,6,7
),
hl as (select d, cat, cs, q, ws, ch, listagg(bkt || ':' || n, ',') within group (order by bkt) hist from hb group by 1,2,3,4,5,6)
select to_char(g.d,'YYYY-MM-DD') day, g.cat, g.cs, g.q, g.ws, g.ch,
  g.tickets, g.resolved, g.n4, g.n12, g.n24, g.n48, g.n72, g.n72p, g.reopened, g.res_timed, g.res_mins, g.repeat7, hl.hist
from g left join hl using(d, cat, cs, q, ws, ch)
order by 1
