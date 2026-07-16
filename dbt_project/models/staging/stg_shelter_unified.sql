-- stg_shelter_unified.sql
-- Unions legacy (2017-2020) and current (2021-present) shelter data
-- into one consistent table for all downstream analysis.
--
-- Key decisions:
-- 1. We keep only columns that exist in BOTH schemas for the unified view
--    Richer current-only columns (program_id, service_user_count etc)
--    are available by querying stg_shelter_current directly
-- 2. shelter_name maps to location_name in current schema
-- 3. Legacy has no capacity_actual — we use capacity_funding as fallback
--    and flag it so downstream models can filter if needed
-- 4. This is the table all descriptive and forecasting models should use

with legacy as (
    select
        occupancy_date,
        organization_name,
        shelter_name                        as location_name,
        shelter_address                     as location_address,
        shelter_postal_code                 as location_postal_code,
        program_name,
        sector,
        occupancy,
        capacity_funding                    as capacity_actual,
        capacity_funding,
        occupancy_rate,
        null::varchar                       as capacity_type,
        null::varchar                       as overnight_service_type,
        data_schema_version,
        source_year,
        false                               as has_actual_capacity
    from {{ ref('stg_shelter_legacy') }}
),

current as (
    select
        occupancy_date,
        organization_name,
        location_name,
        location_address,
        location_postal_code,
        program_name,
        sector,
        occupancy,
        capacity_actual,
        capacity_funding,
        occupancy_rate,
        capacity_type,
        overnight_service_type,
        data_schema_version,
        source_year,
        true                                as has_actual_capacity
    from {{ ref('stg_shelter_current') }}
),

unioned as (
    select * from legacy
    union all
    select * from current
)

select * from unioned
