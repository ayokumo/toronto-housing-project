-- stg_shelter_unified.sql
-- Unions legacy (2017-2020) and current (2021-present) shelter data.
--
-- Fix: explicitly cast occupancy_date to date on both sides of UNION ALL
-- DuckDB type resolution across strptime (legacy) and cast (current)
-- was silently mangling 2021 dates to year 0021.

with legacy as (
    select
        occupancy_date::date                    as occupancy_date,
        organization_name,
        shelter_name                            as location_name,
        shelter_address                         as location_address,
        shelter_postal_code                     as location_postal_code,
        program_name,
        sector,
        occupancy,
        capacity_funding                        as capacity_actual,
        capacity_funding,
        occupancy_rate,
        null::varchar                           as capacity_type,
        null::varchar                           as overnight_service_type,
        data_schema_version,
        source_year,
        false                                   as has_actual_capacity
    from {{ ref('stg_shelter_legacy') }}
),

current as (
    select
        occupancy_date::date                    as occupancy_date,
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
        true                                    as has_actual_capacity
    from {{ ref('stg_shelter_current') }}
),

unioned as (
    select * from legacy
    union all
    select * from current
)

select * from unioned
