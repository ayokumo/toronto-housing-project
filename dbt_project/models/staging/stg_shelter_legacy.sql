-- stg_shelter_legacy.sql
-- Cleans and standardises the 2017-2020 shelter occupancy data.
--
-- Key decisions:
-- 1. Rename columns to snake_case to match current schema
-- 2. Cast date string to DATE type
-- 3. Capacity here is FUNDING capacity (only measure available in legacy)
-- 4. We cannot split bed vs room — legacy data has no capacity_type field
--    so we carry a flag to make this limitation explicit downstream

with source as (
    select * from {{ source('raw', 'raw_shelter_occupancy_legacy') }}
),

cleaned as (
    select
        -- Dates
        cast(OCCUPANCY_DATE as date)            as occupancy_date,

        -- Organization & location
        trim(ORGANIZATION_NAME)                 as organization_name,
        trim(SHELTER_NAME)                      as shelter_name,
        trim(SHELTER_ADDRESS)                   as shelter_address,
        trim(SHELTER_CITY)                      as shelter_city,
        trim(SHELTER_POSTAL_CODE)               as shelter_postal_code,
        trim(FACILITY_NAME)                     as facility_name,
        trim(PROGRAM_NAME)                      as program_name,
        upper(trim(SECTOR))                     as sector,

        -- Occupancy & capacity
        -- Legacy data has a single OCCUPANCY and CAPACITY column
        -- We cannot determine if these are beds or rooms
        cast(OCCUPANCY as integer)              as occupancy,
        cast(CAPACITY as integer)               as capacity_funding,
        null::integer                           as capacity_actual,

        -- Derived occupancy rate
        case
            when cast(CAPACITY as integer) > 0
            then round(
                cast(OCCUPANCY as float) / cast(CAPACITY as float) * 100,
                2
            )
            else null
        end                                     as occupancy_rate,

        -- Schema metadata
        'legacy'                                as data_schema_version,
        _source_year                            as source_year

    from source
    where OCCUPANCY_DATE is not null
)

select * from cleaned
