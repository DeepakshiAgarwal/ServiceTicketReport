-- Shared prelude: one row per ticket (deduplicated), created time in IST, last 3 full months + current month.
with params as (
  select convert_timezone('UTC','Asia/Kolkata',sysdate()) now_ist,
         date_trunc('month', convert_timezone('UTC','Asia/Kolkata',sysdate()))::date cur_start,
         to_char(convert_timezone('UTC','Asia/Kolkata',sysdate()),'YYYY-MM') cur_m,
         to_char(dateadd(month,-1,convert_timezone('UTC','Asia/Kolkata',sysdate())),'YYYY-MM') prev_m
), raw as (
  select * replace (convert_timezone('UTC','Asia/Kolkata',ticket_added_time) as ticket_added_time) from PROD_DB.PUBLIC.SERVICE_TICKET_MODEL
  where ticket_added_time >= dateadd(day, -8, dateadd(month, -3, (select cur_start from params)))
  qualify row_number() over (partition by ticket_id order by last_modified_time desc nulls last) = 1
), b as (
  select r.*,
    replace(coalesce(nullif(trim(last_title),''), nullif(trim(first_title),''), 'Unknown'), ' | ', '|') t,
    upper(trim(split_part(t,'|',1))) cat_k,
    upper(trim(iff(contains(t,'|'), split_part(t,'|',2), '(none)'))) sub_k,
    upper(trim(coalesce(nullif(trim(current_queue),''),'Unassigned'))) q_k,
    lag(ticket_added_time) over (partition by coalesce(customer_account_id, customer_mobile) order by ticket_added_time) prev_t
  from raw r
), base as (
  select b.*,
    iff(prev_t is not null and datediff('hour', prev_t, ticket_added_time) <= 168 and coalesce(customer_account_id, customer_mobile) is not null, 1, 0) is_rep7
  from b where ticket_added_time >= dateadd(month, -3, (select cur_start from params))
),
dc as (select cat_k, mode(trim(split_part(t,'|',1))) cat from base group by 1),
ds as (select cat_k, sub_k, mode(trim(iff(contains(t,'|'), split_part(t,'|',2), '(none)'))) sub from base group by 1,2),
dq as (select q_k, mode(trim(coalesce(nullif(trim(current_queue),''),'Unassigned'))) q from base group by 1),
tk as (
  select base.ticket_id, base.ticket_added_time ts, base.ticket_added_time::date d, to_char(base.ticket_added_time,'YYYY-MM') m,
    'W' || least(ceil(day(base.ticket_added_time)/7),5) wk,
    dc.cat, dc.cat || ' › ' || ds.sub cs, dq.q,
    -- Workstream: CX L2 = queue Cx (wins over PFT); PFT = Internet Issues, Partner Misbehavior,
    -- Shifting Request (Shift Within My Home / Shift to New Address only), Others except Other / App not working / Invoice requested.
    -- PFT tickets finally resolved within 5 minutes of creation count as resolved on call and are kept out of PFT.
    case when base.q_k = 'CX' then 'CX L2'
         when base.cat_k in ('INTERNET ISSUES', 'PARTNER MISBEHAVIOR')
           or (base.cat_k = 'SHIFTING REQUEST' and base.sub_k in ('SHIFT WITHIN MY HOME', 'SHIFT TO NEW ADDRESS'))
           or (base.cat_k = 'OTHERS' and base.sub_k not in ('OTHER', 'APP NOT WORKING', 'INVOICE REQUESTED'))
           then iff(base.is_resolved = 1 and base.resolution_period_mins_calendarhrs <= 5, 'PFT – resolved on call', 'PFT')
         else 'Other' end ws,
    -- Chat = TICKET_SOURCE CUSTOMER_CHAT; Call = everything else (IVR / Kapture sources until Jul 17, source left blank since Jul 18).
    iff(upper(trim(base.ticket_source)) = 'CUSTOMER_CHAT', 'Chat', 'Call') ch,
    coalesce(nullif(trim(base.zone),''),'Unknown') zone,
    base.current_partner_account_id pid, base.current_partner_name pname,
    coalesce(nullif(trim(base.ticket_source),''),'App / direct (blank)') src,
    coalesce(base.resolution_tat_bucket,'Not resolved') sla,
    iff(base.is_resolved=1,1,0) rs, iff(base.is_resolved=1, base.resolution_period_mins_calendarhrs, null) rmin,
    iff(coalesce(base.times_reopened,0)>0,1,0) ro, base.is_rep7 rp,
    base.first_resolved_time frt, base.first_reopened_time fro  -- both in the source time zone (UTC), compare only with each other / sysdate()
  from base join dc using(cat_k) join ds using(cat_k,sub_k) join dq using(q_k)
)
