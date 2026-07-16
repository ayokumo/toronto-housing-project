-- stg_weather.sql
-- Cleans Environment Canada daily weather data for Toronto Pearson.
--
-- Key decisions:
-- 1. Column names from ECCC CSVs have special characters (°, /) so we
--    quote them carefully and rename to clean snake_case
-- 2. "M" flags in the data mean missing -- we cast to float which
--    converts "M" to null automatically via try_cast
-- 3. We derive a cold_day flag (mean temp < 0) as a shelter demand proxy
-- 4. We derive a snow_day flag for operational planning context

with source as (
    select * from {{ source('raw', 'raw_weather_daily') }}
),

cleaned as (
    select
        -- Date
        cast("Date/Time" as date)                       as weather_date,

        -- Temperature (°C)
        try_cast("Max Temp (°C)" as float)              as temp_max_c,
        try_cast("Min Temp (°C)" as float)              as temp_min_c,
        try_cast("Mean Temp (°C)" as float)             as temp_mean_c,

        -- Precipitation
        try_cast("Total Precip (mm)" as float)          as precip_total_mm,
        try_cast("Total Rain (mm)" as float)            as precip_rain_mm,
        try_cast("Total Snow (cm)" as float)            as snow_total_cm,

        -- Derived flags for shelter demand analysis
        try_cast("Mean Temp (°C)" as float) < 0         as is_cold_day,
        try_cast("Total Snow (cm)" as float) > 0        as is_snow_day,

        -- Extreme cold (below -10°C mean) -- warming centre trigger threshold
        try_cast("Mean Temp (°C)" as float) < -10       as is_extreme_cold,

        -- Time dimensions
        year(cast("Date/Time" as date))                 as weather_year,
        month(cast("Date/Time" as date))                as weather_month,
        dayofweek(cast("Date/Time" as date))            as day_of_week,

        _source_year

    from source
    where "Date/Time" is not null
        and "Date/Time" != 'Date/Time'  -- remove any header rows
)

select * from cleaned
