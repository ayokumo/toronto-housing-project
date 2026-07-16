-- stg_boc_rates.sql
-- Cleans Bank of Canada policy rate data.
--
-- Key decisions:
-- 1. The policy rate only changes 8 times per year (fixed announcement dates)
--    so most days are just carry-forwards of the same value
-- 2. We add year and month columns for easy joining to monthly datasets
-- 3. We flag rate-change days for event analysis

with source as (
    select * from {{ source('raw', 'raw_boc_interest_rates') }}
),

cleaned as (
    select
        cast(date as date)                          as rate_date,
        policy_rate,

        -- Time dimensions for joining
        year(cast(date as date))                    as rate_year,
        month(cast(date as date))                   as rate_month,

        -- Flag days where the rate actually changed
        policy_rate != lag(policy_rate) over (
            order by cast(date as date)
        )                                           as is_rate_change_day

    from source
)

select * from cleaned
