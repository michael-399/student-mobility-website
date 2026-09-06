# Conceptual Schema

The conceptual design of the database, in the Entity-Relationship notation
introduced in Module 1. The translation into tables, with types and constraints,
is in [`logical_schema.md`](logical_schema.md); the rules referenced as BR-xx are
in [`requirements_and_business_rules.md`](requirements_and_business_rules.md).

The graphical ER diagram is in the project report
(`docs/report.pdf`, section 3).

## 1. Entities

**USER** — a person who signs in. Attributes: `email` (identifier),
`password_hash`, `first_name`, `last_name`, `role`. `role` is single-valued
(BR-01) and takes one of *student*, *coordinator*, *office staff*. The three
roles are one entity because they share every attribute and differ only in what
they may do.

**INSTITUTION** — a partner university abroad, maintained by the Overseas
office. Attributes: `name`, `country`, `city`, `contact_email` (optional),
`is_active`. Identified externally by the triple (`name`, `country`, `city`).

**MOBILITY APPLICATION** — one student's mobility. Attributes:
`academic_year`, `expected_mobility_period`, `optional_note` (optional),
`status`, `actual_arrival_date` and `actual_departure_date` (both optional until
the student reports them).

**STATUS CHANGE** — weak entity, one row per transition of an application's
status. Attributes: `old_status` (absent on the first change), `new_status`,
`changed_at`. Identified by its application plus its own occurrence.

**LEARNING AGREEMENT** — weak entity: one version of the agreed study plan.
Attributes: `version_number` (partial identifier), `file_path`, `uploaded_at`,
`approval_status`, `decision_date` (optional), `rejection_reason` (optional).
Identified by its application plus `version_number`.

**COURSE MAPPING** — weak entity: one foreign course paired with one course in
the Ca' Foscari study plan, inside one agreement version. Attributes:
`foreign_course_code`, `foreign_course_name`, `foreign_course_credits`,
`home_course_code`, `home_course_name`, `home_course_credits`.

**TRANSCRIPT OF RECORDS** — weak entity: the document issued by the host
institution after the stay. Attributes: `file_path`, `uploaded_at`.

**EXAM RESULT** — weak entity: the outcome of one mapped exam. Attributes:
`foreign_grade`, `exam_date`, `recognition_status`, `decision_date` (optional),
`rejection_reason` (optional).

## 2. Relationships

| Relationship | Between | Cardinality | Participation |
|---|---|---|---|
| SUBMITS | USER (student) — MOBILITY APPLICATION | 1 : N | total on the application side (BR-02) |
| SUPERVISES | USER (coordinator) — MOBILITY APPLICATION | 1 : N | total on the application side (BR-03) |
| HOSTED AT | INSTITUTION — MOBILITY APPLICATION | 1 : N | total on the application side (BR-06) |
| HAS HISTORY | MOBILITY APPLICATION — STATUS CHANGE | 1 : N | total on the status-change side |
| AGREES | MOBILITY APPLICATION — LEARNING AGREEMENT | 1 : N | total on the agreement side (BR-15) |
| MAPS | LEARNING AGREEMENT — COURSE MAPPING | 1 : N | total on the mapping side |
| CERTIFIED BY | MOBILITY APPLICATION — TRANSCRIPT OF RECORDS | 1 : 1 | total on the transcript side, optional on the application side |
| GRADED AS | COURSE MAPPING — EXAM RESULT | 1 : 1 | total on the result side, optional on the mapping side |

The optional participations are the phases of the process: an application has no
transcript until the student returns, and a mapping has no result until the exam
is taken and reported.

## 3. Design decisions taken at the conceptual level

**One USER entity, not three.** The three kinds of user carry identical
attributes, and an application must point to exactly one student and exactly one
coordinator; a generalisation into three entities would leave those two
relationships pointing at different entities for no gain. Role is therefore an
attribute, and authorisation is a matter of behaviour, not of structure.

**A modification is a new agreement version, not a new entity.** The brief asks
that the student may propose changes to the plan during the mobility, and that a
rejection restores the previously agreed mapping. Modelling versions of
LEARNING AGREEMENT, each with its own mappings, achieves both without any
separate "modification" entity: the mapping in force is the one belonging to the
highest approved version (BR-13), and rejecting a later version leaves the
earlier approved version untouched (BR-14).

**Documents are files, not modelled content.** The brief states that the
Learning Agreement and the Transcript of Records may be handled as uploaded
files. Each therefore carries a path and an upload timestamp, not a
representation of its contents.

**EXAM RESULT hangs off COURSE MAPPING, not off the application.** A grade is
always the grade of one agreed exam pair. Attaching it to the mapping means a
result automatically belongs to the plan version it was agreed under, which is
what makes recognition decisions apply only to the version in force (BR-24).

**Status history is an entity, not a derived value.** The lifecycle has to be
auditable, and one point in the workflow — approving a plan modification during
an ongoing mobility — depends on whether the pre-departure phase was ever
completed, which the current status alone cannot answer.

## 4. Answers to the open questions

Section 6 of `requirements_and_business_rules.md` listed the points the brief
left open. They were settled as follows:

1. **One role per user** (BR-01). Nothing in the process needs a person to act in
   two roles at once.
2. **Multiple applications per academic year are allowed.** The brief states that
   a student may create one or more applications and sets no such restriction.
3. **A mapping is one foreign course paired with one home course.** Several
   mappings may share a course code, so many-to-many cases are expressible as
   several rows; the pair itself may not repeat inside one plan version.
4. **Grades are stored as free text.** Host institutions grade on incompatible
   scales, and the original mark reported by the transcript is what must be kept.
5. **A closed application is final.** Closure is the last state of the workflow
   and nothing reopens it (BR-09).
6. **Institutions are deactivated, never deleted**, so past applications keep
   pointing at the partner they were made for.
7. **Status history is retained** for auditing, and decision dates and rejection
   reasons are kept on every agreement version and exam result.
