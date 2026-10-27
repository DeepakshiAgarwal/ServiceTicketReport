, pt as (select m, count(*) tot from tk group by 1)
select m period, sla bucket, count(*) tickets, round(count(*)/any_value(pt.tot),4) share_pct from tk join pt using(m) group by 1,2 order by 1,2
