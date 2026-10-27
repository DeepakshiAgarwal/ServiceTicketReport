, pt as (select m, count(*) tot from tk group by 1)
select m period, src channel, count(*) tickets, round(count(*)/any_value(pt.tot),4) share_pct, round(avg(iff(rmin<=1440,1,0)),4) le24_pct, round(sum(ro)/nullif(sum(rs),0),4) reopen_pct
from tk join pt using(m) group by 1,2 order by 1,3 desc
