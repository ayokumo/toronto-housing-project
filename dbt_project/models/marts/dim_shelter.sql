-- dim_shelter.sql
-- One row per unique shelter location.
--
-- We derive this from the current schema (2021+) which has stable
-- location IDs. Legacy shelters are matched by name where possible.
-- This dimension is used to join geographic and organizational context
-- onto the fact table without repeating it on every daily row.

with current_locations as (
    select distinct
        location_id,
        location_name,
        location_address,
        location_postal_code,
        location_city,
        location_province,
        organization_name,
        shelter_group
    from {{ ref('stg_shelter_current') }}
    where location_id is not null
),

-- Rank to get one canonical row per location_id
-- (address/org can change slightly over time; take most recent)
ranked as (
    select
        *,
        row_number() over (
            partition by location_id
            order by location_name
        ) as rn
    from current_locations
),

final as (
    select
        location_id                             as shelter_id,
        location_name                           as shelter_name,
        location_address                        as shelter_address,
        location_postal_code                    as shelter_postal_code,
        location_city                           as shelter_city,
        location_province                       as shelter_province,
        organization_name,
        shelter_group,

        -- Extract FSA (first 3 chars of postal code) for geographic grouping
        left(trim(location_postal_code), 3)     as forward_sortation_area

    from ranked
    where rn = 1
)

select * from final
