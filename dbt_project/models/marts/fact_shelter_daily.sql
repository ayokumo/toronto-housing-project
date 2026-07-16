-- fact_shelter_daily.sql
-- One row per program per day — the core fact table for all shelter analysis.
--
-- Grain: one row = one program on one date
-- This is the table you query for occupancy trends, geographic concentration,
-- seasonal patterns, and forecasting features.
--
-- Key design decisions:
-- 1. We use stg_shelter_unified so we get 2017-present in one table
-- 2. occupancy_rate is recomputed here from actuals, not trusted from source
-- 3. is_effectively_full flags programs at >= 95% capacity
--    (proxy for unmet demand — not the same as turned-away count)
-- 4. We join dim_date for time intelligence without repeating date logic

with shelter as (
    select * from {{ ref('stg_shelter_unified') }}
),

date_dim as (
    select * from {{ ref('dim_date') }}
),

joined as (
    select
        -- Keys
        {{ dbt_utils.generate_surrogate_key([
            'shelter.occupancy_date',
            'shelter.location_name',
            'shelter.program_name'
        ]) }}                                   as fact_id,

        -- Date foreign key
        shelter.occupancy_date,

        -- Location & program attributes
        shelter.organization_name,
        shelter.location_name,
        shelter.location_address,
        shelter.location_postal_code,
        shelter.program_name,
        shelter.sector,
        shelter.overnight_service_type,
        shelter.capacity_type,

        -- Occupancy metrics
        shelter.occupancy,
        shelter.capacity_actual,
        shelter.capacity_funding,
        shelter.occupancy_rate,

        -- Derived flags
        shelter.occupancy_rate >= 95            as is_effectively_full,
        shelter.occupancy > shelter.capacity_actual
                                                as is_over_capacity,
        shelter.has_actual_capacity,

        -- Time intelligence from dim_date
        date_dim.year_number,
        date_dim.month_number,
        date_dim.month_name,
        date_dim.quarter_number,
        date_dim.season,
        date_dim.week_of_year,
        date_dim.is_weekend,

        -- Schema lineage
        shelter.data_schema_version

    from shelter
    left join date_dim
        on shelter.occupancy_date = date_dim.date_day
)

select * from joined
