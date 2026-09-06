# Logical Schema

This document translates the conceptual design in
[`conceptual_schema.md`](conceptual_schema.md) into the relational schema that
the application actually runs on. Every table, column, constraint and enumerated
type described here exists in the code: the SQLAlchemy models live in
`app/models/`, and the schema is created by the Alembic migration
`migrations/versions/1d161edbfb12_initial_mobility_schema.py`.

Business-rule identifiers (BR-xx) refer to
[`requirements_and_business_rules.md`](requirements_and_business_rules.md).

## 1. Overview

Eight tables, in dependency order:

| Table | Purpose |
|---|---|
| `user_account` | Students, academic coordinators and Overseas office staff |
| `institution` | Predefined partner institutions |
| `mobility_application` | One student's mobility, with its lifecycle status |
| `application_status_history` | Audit trail of every status change |
| `learning_agreement` | One version of the agreed study plan, plus its decision |
| `course_mapping` | Foreign course ↔ Ca' Foscari course pair inside one version |
| `transcript_of_records` | The transcript uploaded after the return |
| `exam_result` | Grade, exam date and recognition decision for one mapping |

Four PostgreSQL enumerated types back the status columns:

| Type | Values |
|---|---|
| `user_role` | `student`, `coordinator`, `office_staff` |
| `mobility_period` | `first_semester`, `second_semester`, `full_year` |
| `application_status` | `created`, `waiting_la_approval`, `pre_departure_completed`, `mobility_in_progress`, `under_exam_recognition`, `closed` |
| `approval_status`, `recognition_status` | `pending`, `approved`, `rejected` |

Enumerations are database types rather than free text so an unknown status
cannot be stored at all, and the same vocabulary is shared by the models, the
API payloads and the front end.

## 2. USER_ACCOUNT

Conceptual entity: **User**. One table holds all three roles, because the three
kinds of user share every attribute and differ only in what they are allowed to
do. Splitting them into three tables would have forced the two foreign keys of
`mobility_application` to point at different tables depending on the role.

| Attribute | Type | Constraints |
|---|---|---|
| `user_id` | `BIGINT` | Primary key |
| `email` | `VARCHAR(255)` | Not null, unique |
| `password_hash` | `TEXT` | Not null |
| `first_name` | `VARCHAR(50)` | Not null |
| `last_name` | `VARCHAR(50)` | Not null |
| `user_role` | `user_role` | Not null |

`email` is unique because it is the login identifier. `user_role` is a single
column, not a many-to-many role assignment: BR-01 fixes exactly one role per
user.

No salt column exists. Passwords are hashed with Argon2id
(`app/security.py`), and the encoded hash already contains the salt and the
algorithm parameters (BR-00B, BR-00C). Verification is done by the hashing
library, never by an SQL comparison (BR-00D).

## 3. INSTITUTION

Conceptual entity: **Host institution**.

| Attribute | Type | Constraints |
|---|---|---|
| `institution_id` | `BIGINT` | Primary key |
| `name` | `VARCHAR(255)` | Not null |
| `country` | `VARCHAR(100)` | Not null |
| `city` | `VARCHAR(100)` | Not null |
| `contact_email` | `VARCHAR(255)` | Nullable |
| `is_active` | `BOOLEAN` | Not null, default `true` |

`uq_host_institution_location` makes `(name, country, city)` unique, so the same
partner cannot be entered twice; the triple rather than the name alone allows
two campuses of the same university in different cities.

`is_active` exists so a partnership can end without erasing history. Applications
reference institutions with `ON DELETE RESTRICT`, and a past application must
keep pointing at the institution it was made for, so the office deactivates an
institution instead of deleting it; deactivated institutions disappear from the
list students choose from but remain readable on existing applications.

## 4. MOBILITY_APPLICATION

Conceptual entity: **Mobility application**. The centre of the schema: it
resolves the relationships *submitted by* (student), *supervised by*
(coordinator) and *hosted at* (institution).

| Attribute | Type | Constraints |
|---|---|---|
| `application_id` | `BIGINT` | Primary key |
| `academic_year` | `VARCHAR(9)` | Not null, `YYYY/YYYY` format |
| `optional_note` | `VARCHAR(500)` | Nullable |
| `expected_mobility_period` | `mobility_period` | Not null |
| `host_institution_id` | `BIGINT` | Foreign key to `institution`, `ON DELETE RESTRICT`, not null |
| `coordinator_id` | `BIGINT` | Foreign key to `user_account`, `ON DELETE RESTRICT`, not null |
| `student_id` | `BIGINT` | Foreign key to `user_account`, `ON DELETE RESTRICT`, not null |
| `status` | `application_status` | Not null, default `created` |
| `actual_arrival_date` | `DATE` | Nullable |
| `actual_departure_date` | `DATE` | Nullable |

Constraints:

- `ck_mobility_application_academic_year_format` —
  `academic_year ~ '^[0-9]{4}/[0-9]{4}$'`. The regular expression enforces the
  shape (BR-07); that the second year is the first plus one cannot be expressed
  as a simple pattern and is validated in `app/services/student.py`.
- `ck_mobility_application_actual_dates` — a departure date requires an arrival
  date and cannot precede it (BR-21).

Both foreign keys to `user_account` use `ON DELETE RESTRICT`: an application is
an administrative record, so neither the student nor the coordinator may be
deleted while one exists. The two mandatory foreign keys implement BR-02 and
BR-03 (exactly one student, exactly one coordinator).

The actual dates are nullable because they are unknown until the student
reports them; the expected period, entered at creation, is not.

## 5. APPLICATION_STATUS_HISTORY

Weak entity, existence-dependent on the application. It records the lifecycle
demanded by BR-26 as data rather than only as behaviour.

| Attribute | Type | Constraints |
|---|---|---|
| `history_id` | `BIGINT` | Primary key |
| `application_id` | `BIGINT` | Foreign key to `mobility_application`, `ON DELETE CASCADE`, not null |
| `old_status` | `application_status` | Nullable |
| `new_status` | `application_status` | Not null |
| `changed_at` | `TIMESTAMPTZ` | Not null, default `now()` |

`old_status` is null exactly once per application: on the opening row written
when the application is created. `ON DELETE CASCADE` is correct here because a
history row has no meaning without its application.

The table also answers a question the current status cannot: whether a phase has
*ever* been reached. `app/services/_workflow.py` uses it to tell an initial
Learning Agreement approval (which leaves the application waiting for the
pre-departure check) from a modification approved mid-mobility (which resumes
the mobility instead).

## 6. LEARNING_AGREEMENT

Weak entity, identified by its parent application plus a version number. A
modification proposed during the mobility is not a separate table: it is simply
the next version, which is what makes BR-13 and BR-14 hold without moving rows.

| Attribute | Type | Constraints |
|---|---|---|
| `application_id` | `BIGINT` | Part of primary key; foreign key to `mobility_application`, `ON DELETE CASCADE` |
| `version_number` | `INTEGER` | Part of primary key; greater than zero |
| `file_path` | `TEXT` | Not null |
| `uploaded_at` | `TIMESTAMPTZ` | Not null, default `now()` |
| `approval_status` | `approval_status` | Not null, default `pending` |
| `decision_date` | `DATE` | Nullable |
| `rejection_reason` | `TEXT` | Nullable |

Constraints:

- Composite primary key `(application_id, version_number)`, which gives BR-16
  (version numbers unique within an application) for free.
- `ck_learning_agreement_version_positive` — `version_number > 0`.
- `ck_learning_agreement_decision_consistency` — the three legal shapes of a
  decision: pending has neither date nor reason (BR-17); approved has a date and
  no reason (BR-18); rejected has both a date and a non-empty reason (BR-19).
  Encoding this as one CHECK keeps the three nullable columns from drifting into
  a meaningless combination.

Only the file path is stored, not the document itself: the brief does not
require modelling the content of the agreement, and keeping binaries out of the
database keeps backups and queries small. The uploaded file is written under a
collision-resistant name by `app/storage.py`.

The full version history is retained, so every superseded plan and the reason it
was rejected stay auditable.

## 7. COURSE_MAPPING

Weak entity, existence-dependent on one Learning Agreement version. It carries
the exam mapping required before departure.

| Attribute | Type | Constraints |
|---|---|---|
| `mapping_id` | `BIGINT` | Primary key |
| `application_id` | `BIGINT` | Part of composite foreign key; not null |
| `version_number` | `INTEGER` | Part of composite foreign key; not null |
| `foreign_course_code` | `VARCHAR(50)` | Not null |
| `foreign_course_name` | `VARCHAR(255)` | Not null |
| `foreign_course_credits` | `NUMERIC(4,1)` | Not null, greater than zero |
| `home_course_code` | `VARCHAR(50)` | Not null |
| `home_course_name` | `VARCHAR(255)` | Not null |
| `home_course_credits` | `NUMERIC(4,1)` | Not null, greater than zero |

Constraints:

- `fk_course_mapping_learning_agreement` — `(application_id, version_number)`
  references `learning_agreement(application_id, version_number)` with
  `ON DELETE CASCADE`: a mapping has no meaning without its agreement version.
- `ck_course_mapping_home_credits_positive`,
  `ck_course_mapping_foreign_credits_positive` — both credit values are positive
  (BR-11).
- `uq_course_mapping_plan_course_pair` — `(application_id, version_number,
  home_course_code, foreign_course_code)` is unique, so the same pair cannot
  appear twice in one plan version.

A surrogate `mapping_id` is kept alongside the composite foreign key because
`exam_result` references a single mapping and the API addresses mappings by id.

Credits are `NUMERIC(4,1)`, not integers: ECTS values such as 7.5 are common.
The two credit values are stored separately because the brief requires both and
never states that they must be equal.

## 8. TRANSCRIPT_OF_RECORDS

Weak entity: at most one transcript per application, uploaded after the return.

| Attribute | Type | Constraints |
|---|---|---|
| `transcript_id` | `BIGINT` | Primary key |
| `application_id` | `BIGINT` | Foreign key to `mobility_application`, `ON DELETE CASCADE`, not null, unique |
| `file_path` | `TEXT` | Not null |
| `uploaded_at` | `TIMESTAMPTZ` | Not null, default `now()` |

The unique constraint on `application_id` is what makes the relationship
one-to-one (BR-15): re-uploading replaces the stored path on the existing row
rather than adding a second transcript. As with the Learning Agreement, only the
path is stored.

## 9. EXAM_RESULT

Weak entity, one result per course mapping: the grade obtained abroad and the
coordinator's recognition decision on it.

| Attribute | Type | Constraints |
|---|---|---|
| `result_id` | `BIGINT` | Primary key |
| `mapping_id` | `BIGINT` | Foreign key to `course_mapping`, `ON DELETE CASCADE`, not null, unique |
| `foreign_grade` | `VARCHAR(50)` | Not null |
| `exam_date` | `DATE` | Not null |
| `recognition_status` | `recognition_status` | Not null, default `pending` |
| `decision_date` | `DATE` | Nullable |
| `rejection_reason` | `TEXT` | Nullable |

Constraints:

- Unique `mapping_id`, giving the one-to-one relationship with `course_mapping`.
- `ck_exam_result_decision_consistency` — the same three legal decision shapes as
  the Learning Agreement (BR-17, BR-18, BR-19).

`foreign_grade` is free text of up to 50 characters because host institutions
grade on incompatible scales (30/30, A–F, pass/fail); normalising them would
require a conversion table the brief does not ask for, and would lose the
original mark that the transcript actually reports.

Because a result hangs off a mapping, and a mapping belongs to one agreement
version, a result is automatically tied to the plan version it was agreed
under. That is what BR-24 needs: only results attached to the version currently
in force can be decided.

## 10. Relationship summary

| Relationship | Cardinality | Implementation |
|---|---|---|
| Student — Application | 1 : N, total on the application side | `mobility_application.student_id` |
| Coordinator — Application | 1 : N, total on the application side | `mobility_application.coordinator_id` |
| Institution — Application | 1 : N, total on the application side | `mobility_application.host_institution_id` |
| Application — Status history | 1 : N, total on the history side | `application_status_history.application_id` |
| Application — Learning Agreement | 1 : N, total on the agreement side | Composite key `(application_id, version_number)` |
| Learning Agreement — Course mapping | 1 : N, total on the mapping side | Composite foreign key |
| Course mapping — Exam result | 1 : 1 (optional result) | Unique `exam_result.mapping_id` |
| Application — Transcript | 1 : 1 (optional transcript) | Unique `transcript_of_records.application_id` |

Deletion behaviour follows the same division: everything that exists only as
part of an application cascades with it, while the entities an application
merely refers to — users and institutions — are protected with `RESTRICT`.

## 11. Rules the schema does not enforce

Some rules cannot be expressed as a table constraint because they depend on more
than one row, or on who is asking. They are enforced in the service layer and
listed here so the boundary is explicit:

| Rule | Where enforced |
|---|---|
| BR-04, BR-05: a student reaches only their own applications, a coordinator only those assigned to them | Scoped queries in `app/repositories.py` |
| BR-07 (second half): the second academic year is the first plus one | `app/services/student.py` |
| BR-12: the mapping is not editable while a version awaits a decision | `app/services/student.py` |
| BR-20: no pre-departure sign-off without an approved agreement | `app/services/office.py` |
| BR-22: the exam date falls inside the mobility period | `app/services/student.py` |
| BR-23, BR-25: recognition needs the transcript; closure needs every result decided | `app/services/student.py`, `app/services/office.py` |
| BR-26: status changes follow the permitted workflow | `app/services/_workflow.py` |

Every request runs inside one transaction, opened by Flask-SQLAlchemy and
committed or rolled back once in `app/__init__.py`, so a request that violates
one of these rules leaves no partial write behind.
