-- stg_shelter_current.sql
-- Cleans and standardises the 2021-present shelter occupancy data.
--
-- Key decisions:
-- 1. The current schema separates bed-based and room-based programs
--    We compute a unified occupancy/capacity by coalescing bed then room
-- 2. We keep the raw bed/room splits for downstream granular analysis
-- 3. CAPACITY_ACTUAL is used (not CAPACITY_FUNDING) — actual is what matters
--    for real utilization; funding capacity can overstate available beds

with source as (
    select * from {{ source('raw', 'raw_shelter_occupancy') }}
),

cleaned as (
    select
        -- Dates
        cast(OCCUPANCY_DATE as date)                as occupancy_date,

        -- Organization & location
        cast(ORGANIZATION_ID as integer)            as organization_id,
        trim(ORGANIZATION_NAME)                     as organization_name,
        cast(SHELTER_ID as integer)                 as shelter_id,
        trim(SHELTER_GROUP)                         as shelter_group,
        cast(LOCATION_ID as integer)                as location_id,
        trim(LOCATION_NAME)                         as location_name,
        trim(LOCATION_ADDRESS)                      as location_address,
        trim(LOCATION_POSTAL_CODE)                  as location_postal_code,
        trim(LOCATION_CITY)                         as location_city,
        trim(LOCATION_PROVINCE)                     as location_province,
        cast(PROGRAM_ID as integer)                 as program_id,
        trim(PROGRAM_NAME)                          as program_name,
        upper(trim(SECTOR))                         as sector,
        trim(PROGRAM_MODEL)                         as program_model,
        trim(OVERNIGHT_SERVICE_TYPE)                as overnight_service_type,
        trim(PROGRAM_AREA)                          as program_area,

        -- Capacity type tells us which columns are populated
        trim(CAPACITY_TYPE)                         as capacity_type,

        -- Bed-based fields
        cast(CAPACITY_ACTUAL_BED as integer)        as capacity_actual_bed,
        cast(CAPACITY_FUNDING_BED as integer)       as capacity_funding_bed,
        cast(OCCUPIED_BEDS as integer)              as occupied_beds,
        cast(UNOCCUPIED_BEDS as integer)            as unoccupied_beds,

        -- Room-based fields
        cast(CAPACITY_ACTUAL_ROOM as integer)       as capacity_actual_room,
        cast(CAPACITY_FUNDING_ROOM as integer)      as capacity_funding_room,
        cast(OCCUPIED_ROOMS as integer)             as occupied_rooms,
        cast(UNOCCUPIED_ROOMS as integer)           as unoccupied_rooms,

        -- Unified occupancy & capacity (coalesce bed then room)
        -- This gives us one number regardless of capacity_type
        coalesce(
            cast(OCCUPIED_BEDS as integer),
            cast(OCCUPIED_ROOMS as integer)
        )                                           as occupancy,

        coalesce(
            cast(CAPACITY_ACTUAL_BED as integer),
            cast(CAPACITY_ACTUAL_ROOM as integer)
        )                                           as capacity_actual,

        coalesce(
            cast(CAPACITY_FUNDING_BED as integer),
            cast(CAPACITY_FUNDING_ROOM as integer)
        )                                           as capacity_funding,

        -- Unified occupancy rate (recompute from actuals, don't trust pre-calc)
        case
            when coalesce(
                cast(CAPACITY_ACTUAL_BED as integer),
                cast(CAPACITY_ACTUAL_ROOM as integer)
            ) > 0
            then round(
                cast(coalesce(
                    cast(OCCUPIED_BEDS as integer),
                    cast(OCCUPIED_ROOMS as integer)
                ) as float)
                /
                cast(coalesce(
                    cast(CAPACITY_ACTUAL_BED as integer),
                    cast(CAPACITY_ACTUAL_ROOM as integer)
                ) as float)
                * 100,
                2
            )
            else null
        end                                         as occupancy_rate,

        -- Service user count (individuals, may exceed capacity for room programs)
        cast(SERVICE_USER_COUNT as integer)         as service_user_count,

        -- Schema metadata
        'current'                                   as data_schema_version,
        year(cast(OCCUPANCY_DATE as date))          as source_year

    from source
    where OCCUPANCY_DATE is not null
)

select * from cleaned
