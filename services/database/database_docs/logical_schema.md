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

## LearningAgreement

Represents one uploaded Learning Agreement and the exam plan contained in that
version. A new version is created when the student proposes a modification.
Keeping old versions ensures that rejecting a modification does not overwrite
the previously approved agreement and mappings.

Attributes:

- mobility application
- version number
- uploaded file path
- upload timestamp
- approval status
- decision date
- rejection reason

Relationships:

- One mobility application can have many Learning Agreement versions.
- Each Learning Agreement belongs to exactly one mobility application.
- One Learning Agreement version contains one or more course mappings.

## LEARNING_AGREEMENT

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `application_id` | `BIGINT` | Composite primary key; foreign key to `MOBILITY_APPLICATION.application_id`; not null; delete cascades |
| `version_number` | `INTEGER` | Composite primary key; positive integer |
| `file_path` | `TEXT` | Not null |
| `uploaded_at` | `TIMESTAMP WITH TIME ZONE` | Not null, defaults to current time |
| `approval_status` | `APPROVAL_STATUS` | Not null, default `pending` |
| `decision_date` | `DATE` | Optional while pending; required after a decision |
| `rejection_reason` | `TEXT` | Required when rejected; otherwise optional |

The pair `(application_id, version_number)` uniquely identifies a Learning
Agreement version. Version numbers therefore restart at `1` for each mobility
application.

Allowed `APPROVAL_STATUS` values:

- `pending`
- `approved`
- `rejected`

Decision consistency rules:

- A pending version must not have a decision date.
- An approved or rejected version must have a decision date.
- A rejected version must have a non-empty rejection reason.

## CourseMapping

Represents the association between one foreign course and one Ca' Foscari home
course within a specific Learning Agreement version. Different agreement
versions may contain different numbers of mappings.

Attributes:

- mapping identifier
- Learning Agreement version
- foreign course code
- foreign course name
- foreign course credits
- home course code
- home course name
- home course credits

Relationships:

- One Learning Agreement version can contain many course mappings.
- Each course mapping belongs to exactly one Learning Agreement version.

## COURSE_MAPPING

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `mapping_id` | `BIGINT` | Primary key |
| `application_id` | `BIGINT` | Composite foreign key to `LEARNING_AGREEMENT`; not null |
| `version_number` | `INTEGER` | Composite foreign key to `LEARNING_AGREEMENT`; not null |
| `foreign_course_code` | `VARCHAR(50)` | Not null |
| `foreign_course_name` | `VARCHAR(255)` | Not null |
| `foreign_course_credits` | `NUMERIC(4,1)` | Not null, greater than zero |
| `home_course_code` | `VARCHAR(50)` | Not null |
| `home_course_name` | `VARCHAR(255)` | Not null |
| `home_course_credits` | `NUMERIC(4,1)` | Not null, greater than zero |

The pair `(application_id, version_number)` is a composite foreign key to
`LEARNING_AGREEMENT(application_id, version_number)`. Deleting a Learning
Agreement version cascades to its mappings because a mapping has no meaning
without its agreement.

The combination `(application_id, version_number, home_course_code,
foreign_course_code)` must be unique, preventing the same course pair from being
entered twice in one plan version. The two credit values are stored separately
because the project brief requires both and does not state that they must be
equal.
