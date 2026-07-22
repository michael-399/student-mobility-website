# Conceptual Entities

## User

Represents a person who can authenticate and use the platform.

Shared attributes:

- user identifier
- email address
- password hash
- first name
- last name
- user role

The plaintext password is never stored. The application hashes passwords using
Argon2id. The Argon2 library generates a unique random salt for each password and
includes the salt and algorithm parameters in the encoded hash stored in
`password_hash`.

# Preliminary Logical Schema

## USER_ACCOUNT

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `user_id` | `BIGINT` | Primary key |
| `email` | `VARCHAR(255)` | Not null, unique |
| `password_hash` | `TEXT` | Not null |
| `first_name` | `VARCHAR(100)` | Not null |
| `last_name` | `VARCHAR(100)` | Not null |
| `user_role` | `USER_ROLE` | Not null |

Allowed `USER_ROLE` values:

- `student`
- `coordinator`
- `office_staff`

Authentication is performed in Python rather than in PostgreSQL:

1. Registration: hash the plaintext password with Argon2id and store only the
   resulting encoded hash.
2. Login: retrieve the encoded hash by email and ask the Argon2 library to verify
   the submitted plaintext password against it.
3. Never manually extract, concatenate, or compare the salt and password.

## HostInstitution

Represents a partner university abroad that can host students during an Overseas mobility.

Shared attributes:

- UNI identifier
- UNI name
- UNI Contact Email
- Country
- City

## HOST_INSTITUTION

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `institution_id` | `BIGINT` | Primary key |
| `name` | `VARCHAR(255)` | Not null |
| `country` | `VARCHAR(100)` | Not null |
| `city` | `VARCHAR(100)` | Not null |
| `contact_email` | `VARCHAR(255)` | Optional |
| `is_active` | `BOOLEAN` | Not null, default true |

The combination of `name`, `country`, and `city` must be unique. An institution
that is referenced by a mobility application cannot be deleted; it can be made
inactive instead.

## MobilityApplication

Represents one student's request to complete an Overseas mobility at one host
institution under the responsibility of one academic coordinator.

Attributes:

- application identifier
- student
- academic coordinator
- host institution
- academic year
- expected mobility period
- optional notes
- actual arrival date
- actual departure date
- application status

Relationships:

- One student can create many mobility applications; each application belongs to
  exactly one student.
- One coordinator can supervise many mobility applications; each application is
  assigned to exactly one coordinator.
- One host institution can be selected by many mobility applications; each
  application selects exactly one host institution.

## MOBILITY_APPLICATION

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `application_id` | `BIGINT` | Primary key |
| `student_id` | `BIGINT` | Foreign key to `USER_ACCOUNT.user_id`, not null |
| `coordinator_id` | `BIGINT` | Foreign key to `USER_ACCOUNT.user_id`, not null |
| `host_institution_id` | `BIGINT` | Foreign key to `HOST_INSTITUTION.institution_id`, not null, delete restricted |
| `academic_year` | `VARCHAR(9)` | Not null, format `YYYY/YYYY` with consecutive years |
| `expected_period` | `MOBILITY_PERIOD` | Not null |
| `notes` | `TEXT` | Optional |
| `actual_arrival_date` | `DATE` | Optional |
| `actual_departure_date` | `DATE` | Optional; must not precede arrival date |
| `status` | `APPLICATION_STATUS` | Not null, default `created` |

Allowed `MOBILITY_PERIOD` values:

- `first_semester`
- `second_semester`
- `full_year`

Initial `APPLICATION_STATUS` values:

- `created`
- `waiting_la_approval`
- `pre_departure_completed`
- `mobility_in_progress`
- `under_exam_recognition`
- `closed`

The `student_id` and `coordinator_id` foreign keys both reference
`USER_ACCOUNT.user_id`. Additional database or application rules must ensure that
the referenced users have the `student` and `coordinator` roles respectively.

## EXAM_MAPPING

Attributes: 
- application_id
- foreign_course
- home_course
- credits 
