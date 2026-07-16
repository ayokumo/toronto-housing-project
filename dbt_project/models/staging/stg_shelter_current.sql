-- stg_shelter_current.sql
-- Cleans and standardises the 2021-present shelter occupancy data.
-- Fix: empty string '' in bed/room columns -- use try_cast throughout

with source as (
    select * from {{ source('raw', 'raw_shelter_occupancy') }}
),

cleaned as (
    select
        cast(OCCUPANCY_DATE as date)                    as occupancy_date,
        try_cast(ORGANIZATION_ID as integer)            as organization_id,
        trim(ORGANIZATION_NAME)                         as organization_name,
        try_cast(SHELTER_ID as integer)                 as shelter_id,
        trim(SHELTER_GROUP)                             as shelter_group,
        try_cast(LOCATION_ID as integer)                as location_id,
        trim(LOCATION_NAME)                             as location_name,
        trim(LOCATION_ADDRESS)                          as location_address,
        trim(LOCATION_POSTAL_CODE)                      as location_postal_code,
        trim(LOCATION_CITY)                             as location_city,
        trim(LOCATION_PROVINCE)                         as location_province,
        try_cast(PROGRAM_ID as integer)                 as program_id,
        trim(PROGRAM_NAME)                              as program_name,
        upper(trim(SECTOR))                             as sector,
        trim(PROGRAM_MODEL)                             as program_model,
        trim(OVERNIGHT_SERVICE_TYPE)                    as overnight_service_type,
        trim(PROGRAM_AREA)                              as program_area,
        trim(CAPACITY_TYPE)                             as capacity_type,
        try_cast(CAPACITY_ACTUAL_BED as integer)        as capacity_actual_bed,
        try_cast(CAPACITY_FUNDING_BED as integer)       as capacity_funding_bed,
        try_cast(OCCUPIED_BEDS as integer)              as occupied_beds,
        try_cast(UNOCCUPIED_BEDS as integer)            as unoccupied_beds,
        try_cast(CAPACITY_ACTUAL_ROOM as integer)       as capacity_actual_room,
        try_cast(CAPACITY_FUNDING_ROOM as integer)      as capacity_funding_room,
        try_cast(OCCUPIED_ROOMS as integer)             as occupied_rooms,
        try_cast(UNOCCUPIED_ROOMS as integer)           as unoccupied_rooms,
        coalesce(
            try_cast(OCCUPIED_BEDS as integer),
            try_cast(OCCUPIED_ROOMS as integer)
        )                                               as occupancy,
        coalesce(
            try_cast(CAPACITY_ACTUAL_BED as integer),
            try_cast(CAPACITY_ACTUAL_ROOM as integer)
        )                                               as capacity_actual,
        coalesce(
            try_cast(CAPACITY_FUNDING_BED as integer),
            try_cast(CAPACITY_FUNDING_ROOM as integer)
        )                                               as capacity_funding,
        case
            when coalesce(
                try_cast(CAPACITY_ACTUAL_BED as integer),
                try_cast(CAPACITY_ACTUAL_ROOM as integer)
            ) > 0
            then round(
                cast(coalesce(
                    try_cast(OCCUPIED_BEDS as integer),
                    try_cast(OCCUPIED_ROOMS as integer)
                ) as float)
                /
                cast(coalesce(
                    try_cast(CAPACITY_ACTUAL_BED as integer),
                    try_cast(CAPACITY_ACTUAL_ROOM as integer)
                ) as float)
                * 100,
                2
            )
            else null
        end                                             as occupancy_rate,
        try_cast(SERVICE_USER_COUNT as integer)         as service_user_count,
        'current'                                       as data_schema_version,
        year(cast(OCCUPANCY_DATE as date))              as source_year
    from source
    where OCCUPANCY_DATE is not null
)

select * from cleaned
