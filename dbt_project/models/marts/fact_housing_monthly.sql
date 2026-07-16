-- fact_housing_monthly.sql
-- Monthly housing market metrics for trend and regression analysis.
--
-- Grain: one row per month
-- Joins shelter system aggregates with Bank of Canada policy rate.
-- CMHC rental data is annual so we forward-fill within each year
-- (a rate from October survey applies to all months of that year).
--
-- This is the table for Question 2:
-- "How do housing market forces relate to homelessness indicators?"

with shelter_monthly as (
    -- Aggregate daily shelter data to monthly
    select
        date_trunc('month', occupancy_date)::date   as month_start,
        year_number                                  as year_number,
        month_number                                 as month_number,

        -- System-wide occupancy metrics
        round(avg(occupancy_rate), 2)                as avg_occupancy_rate,
        sum(occupancy)                               as total_occupied,
        sum(capacity_actual)                         as total_capacity,
        round(
            sum(occupancy)::float
            / nullif(sum(capacity_actual), 0) * 100,
            2
        )                                            as system_occupancy_rate,

        -- Stress indicators
        count(*) filter (
            where is_effectively_full
        )                                            as programs_effectively_full,
        count(*)                                     as total_programs,
        round(
            count(*) filter (where is_effectively_full)::float
            / nullif(count(*), 0) * 100,
            2
        )                                            as pct_programs_full,

        -- Sector breakdown
        sum(occupancy) filter (
            where sector = 'FAMILIES'
        )                                            as families_occupied,
        sum(occupancy) filter (
            where sector = 'YOUTH'
        )                                            as youth_occupied,
        sum(occupancy) filter (
            where sector = 'WOMEN'
        )                                            as women_occupied,
        sum(occupancy) filter (
            where sector = 'MEN'
        )                                            as men_occupied

    from {{ ref('fact_shelter_daily') }}
    group by 1, 2, 3
),

boc_monthly as (
    -- Average policy rate within each month
    select
        date_trunc('month', rate_date)::date        as month_start,
        round(avg(policy_rate), 4)                  as avg_policy_rate,
        max(policy_rate) - min(policy_rate) > 0     as rate_changed_this_month
    from {{ ref('stg_boc_rates') }}
    group by 1
),

weather_monthly as (
    -- Monthly weather aggregates
    select
        date_trunc('month', weather_date)::date     as month_start,
        round(avg(temp_mean_c), 2)                  as avg_temp_c,
        round(min(temp_min_c), 2)                   as min_temp_c,
        sum(snow_total_cm)                          as total_snow_cm,
        count(*) filter (where is_cold_day)         as cold_days,
        count(*) filter (where is_extreme_cold)     as extreme_cold_days
    from {{ ref('stg_weather') }}
    group by 1
),

final as (
    select
        sm.month_start,
        sm.year_number,
        sm.month_number,

        -- Shelter metrics
        sm.avg_occupancy_rate,
        sm.total_occupied,
        sm.total_capacity,
        sm.system_occupancy_rate,
        sm.programs_effectively_full,
        sm.total_programs,
        sm.pct_programs_full,
        sm.families_occupied,
        sm.youth_occupied,
        sm.women_occupied,
        sm.men_occupied,

        -- Interest rate
        boc.avg_policy_rate,
        boc.rate_changed_this_month,

        -- Weather
        wm.avg_temp_c,
        wm.min_temp_c,
        wm.total_snow_cm,
        wm.cold_days,
        wm.extreme_cold_days

    from shelter_monthly sm
    left join boc_monthly boc
        on sm.month_start = boc.month_start
    left join weather_monthly wm
        on sm.month_start = wm.month_start
)

select * from final
