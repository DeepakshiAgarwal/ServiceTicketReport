select dayofweekiso(ts) dow, decode(dayofweekiso(ts),1,'Mon',2,'Tue',3,'Wed',4,'Thu',5,'Fri',6,'Sat','Sun') weekday, hour(ts) hour, count(*) tickets
from tk where m = (select cur_m from params) group by 1,2,3 order by 1,3
