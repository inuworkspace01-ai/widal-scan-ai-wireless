-- WIDAL-SCAN AI initial account policy.
-- Login IDs are stored lowercase; display_name preserves the requested casing.
-- This migration disables the superseded starter accounts and leaves one admin.

begin;

update public.profiles
set is_active = false
where lower(username) in ('inu', 'lab');

update public.profiles
set role = 'atlm'
where role = 'admin'
  and lower(username) <> 'inuu';

update public.profiles
set display_name = 'Inuu',
    role = 'admin',
    is_active = true
where lower(username) = 'inuu';

comment on column public.profiles.username is
  'Normalized lowercase login ID. The display_name field preserves account display casing.';

commit;
