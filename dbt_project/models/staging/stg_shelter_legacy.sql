-- stg_shelter_legacy.sql
-- Cleans and standardises the 2017-2020 shelter occupancy data.
--
-- Date format finding: mixed formats in source data
--   2017-2019: "2017-01-01T00:00:00" (ISO with time component)
--   2020:      "01/01/2020" (MM/DD/YYYY)
-- We handle both with a case statement

with source as (
    select * from {{ source('raw', 'raw_shelter_occupancy_legacy') }}
),

cleaned as (
    select
        -- Dates: handle two formats present in source data
        case
            when OCCUPANCY_DATE like '%/%'
            then strptime(OCCUPANCY_DATE, '%m/%d/%Y')::date
            else cast(OCCUPANCY_DATE as date)
        end                                         as occupancy_date,

        -- Organization & location
        trim(ORGANIZATION_NAME)                     as organization_name,
        trim(SHELTER_NAME)                          as shelter_name,
        trim(SHELTER_ADDRESS)                       as shelter_address,
        trim(SHELTER_CITY)                          as shelter_city,
        trim(SHELTER_POSTAL_CODE)                   as shelter_postal_code,
        trim(FACILITY_NAME)                         as facility_name,
        trim(PROGRAM_NAME)                          as program_name,
        upper(trim(SECTOR))                         as sector,

        -- Occupancy & capacity
        try_cast(OCCUPANCY as integer)              as occupancy,
        try_cast(CAPACITY as integer)               as capacity_funding,
        null::integer                               as capacity_actual,

        -- Derived occupancy rate
        case
            when try_cast(CAPACITY as integer) > 0
            then round(
                try_cast(OCCUPANCY as float)
                / try_cast(CAPACITY as float) * 100,
                2
            )
            else null
        end                                         as occupancy_rate,

        'legacy'                                    as data_schema_version,
        _source_year                                as source_year

    from source
    where OCCUPANCY_DATE is not null
        and trim(OCCUPANCY_DATE) != ''
)

select * from cleaned
