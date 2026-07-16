-- dim_date.sql
-- Calendar dimension covering the full range of shelter data (2017-present).
--
-- Why a date dimension?
-- Joining to this table lets you filter/group by week, month, quarter,
-- season, or fiscal year without writing EXTRACT() logic in every query.
-- It's the "free" dimension that makes time-intelligence trivial.

with date_spine as (
    -- Generate one row per day from 2017-01-01 to today
    select unnest(
        generate_series(
            date '2017-01-01',
            current_date,
            interval '1 day'
        )
    )::date as date_day
),

enriched as (
    select
        -- Primary key
        date_day,

        -- Year/month/day components
        year(date_day)                          as year_number,
        month(date_day)                         as month_number,
        day(date_day)                           as day_of_month,

        -- Week
        weekofyear(date_day)                    as week_of_year,
        dayofweek(date_day)                     as day_of_week,      -- 0=Sun, 6=Sat
        dayname(date_day)                       as day_name,
        monthname(date_day)                     as month_name,

        -- Quarter
        quarter(date_day)                       as quarter_number,
        'Q' || quarter(date_day)                as quarter_label,

        -- Season (meteorological, Northern Hemisphere)
        case month(date_day)
            when 12 then 'Winter'
            when 1  then 'Winter'
            when 2  then 'Winter'
            when 3  then 'Spring'
            when 4  then 'Spring'
            when 5  then 'Spring'
            when 6  then 'Summer'
            when 7  then 'Summer'
            when 8  then 'Summer'
            when 9  then 'Fall'
            when 10 then 'Fall'
            when 11 then 'Fall'
        end                                     as season,

        -- Fiscal year (City of Toronto: Jan 1 - Dec 31, same as calendar)
        year(date_day)                          as fiscal_year,

        -- Useful flags
        dayofweek(date_day) in (0, 6)           as is_weekend,
        date_day = date_trunc('month', date_day) as is_month_start,
        date_day = (date_trunc('month', date_day)
            + interval '1 month'
            - interval '1 day')::date           as is_month_end

    from date_spine
)

select * from enriched
