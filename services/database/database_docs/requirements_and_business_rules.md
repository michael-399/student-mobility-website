# Requirements and Business Rules

## 1. Purpose

The system manages the main administrative phases of an Overseas mobility:

1. before departure;
2. during the mobility;
3. after return and exam recognition.

This document translates the project brief into requirements and testable business
rules. It will be refined before creating the conceptual and logical schemas.

## 2. Actors and permissions

### Student

- Creates and views their own mobility applications.
- Selects a host institution and academic coordinator.
- Defines the proposed mapping between foreign and Ca' Foscari courses.
- Uploads Learning Agreements and the Transcript of Records.
- Records actual mobility dates, exam grades, and exam dates.
- Cannot view or modify another student's applications.

### Academic coordinator

- Views applications assigned to them.
- Approves or rejects Learning Agreements and their modifications.
- Records a reason when rejecting a Learning Agreement or modification.
- Approves or rejects exam recognition results.
- Cannot decide applications assigned to another coordinator.

### Overseas office staff

- Views all applications.
- Manages the predefined list of partner institutions.
- Completes the pre-departure check.
- Closes applications when all required steps are complete.

## 3. Functional requirements

### FR-01: User management

The system shall distinguish students, academic coordinators, and Overseas office
staff and shall enforce the permissions described above.

### FR-02: Host institution management

Office staff shall manage partner institutions. Each institution shall have at
least a name, country, and city. A student shall select an institution from this
predefined list.

### FR-03: Mobility application creation

A student shall be able to create one or more applications. Each application
shall contain an academic year, host institution, expected mobility period,
academic coordinator, and optional notes.

### FR-04: Proposed exam mapping

An application shall contain one or more proposed mappings between a foreign
course and a course in the student's Ca' Foscari study plan. Each side shall
include a course code, title, and number of credits.

### FR-05: Learning Agreement

A student shall upload a signed Learning Agreement. The assigned coordinator
shall approve or reject it and record the decision date. A rejection shall
include a reason.

### FR-06: Pre-departure check

Office staff shall mark the pre-departure phase complete only after the essential
application data and an approved Learning Agreement exist.

### FR-07: Mobility dates

During the mobility, the student shall record the actual arrival and departure
dates at the host institution.

### FR-08: Learning Agreement modifications

During the mobility, the student shall propose changes to the exam mappings and
upload a new Learning Agreement version. The assigned coordinator shall approve
or reject each proposal. Rejection shall leave the previously approved mapping
unchanged.

### FR-09: Transcript and exam results

After returning, the student shall upload a Transcript of Records and record the
grade and passing date for the relevant foreign exams.

### FR-10: Exam recognition

The assigned coordinator shall approve or reject each proposed exam recognition
and its grade.

### FR-11: Application closure

Office staff shall close an application only after the Transcript of Records has
been uploaded and every submitted exam has received a recognition decision.

### FR-12: Application status

The system shall track the current lifecycle status of every application. The
initial set of statuses is:

- `created`
- `waiting_la_approval`
- `pre_departure_completed`
- `mobility_in_progress`
- `under_exam_recognition`
- `closed`

## 4. Business rules

Business rules describe conditions that must always remain true. The enforcement
mechanism will be chosen during logical design.

### Users and ownership

- BR-01: Every user shall have exactly one system role.
- BR-02: Every mobility application shall belong to exactly one student.
- BR-03: Every mobility application shall be assigned to exactly one academic
  coordinator.
- BR-04: Only the owner student may change student-editable data in an
  application.
- BR-05: Only the assigned coordinator may make academic decisions for an
  application.

### Institutions and applications

- BR-06: Every application shall refer to exactly one predefined host
  institution.
- BR-07: An academic year shall use the format `YYYY/YYYY`, and the second year
  shall be the first year plus one.
- BR-08: The expected mobility period shall be first semester, second semester,
  or full year.
- BR-09: A closed application shall not be modified.

### Course mappings

- BR-10: A proposed course mapping shall belong to exactly one application.
- BR-11: Course codes and titles shall not be empty, and credits shall be
  positive.
- BR-12: The exam mapping shall not be editable while its Learning Agreement is
  waiting for a decision.
- BR-13: An approved modification shall become the current mapping.
- BR-14: A rejected modification shall not replace the previously approved
  mapping.

### Documents and decisions

- BR-15: Every uploaded document shall belong to exactly one application.
- BR-16: Learning Agreement version numbers shall be unique within an
  application.
- BR-17: A pending decision shall not have a decision date.
- BR-18: An approved or rejected decision shall have a decision date.
- BR-19: A rejected decision shall include a non-empty reason.
- BR-20: The pre-departure phase shall not be completed without an approved
  Learning Agreement.

### Dates, recognition, and closure

- BR-21: An actual departure date shall not be earlier than the actual arrival
  date.
- BR-22: An exam passing date shall be within the actual mobility period when
  both mobility dates are known.
- BR-23: Exam recognition shall not begin before a Transcript of Records has
  been uploaded.
- BR-24: Every exam recognition decision shall refer to an exam in the current
  approved mapping.
- BR-25: An application shall not be closed while any submitted exam recognition
  is pending.
- BR-26: Application status changes shall follow the permitted workflow and
  shall not skip required phases.

## 5. Preliminary workflow

```text
created
  -> waiting_la_approval
  -> pre_departure_completed
  -> mobility_in_progress
  -> under_exam_recognition
  -> closed
```

Rejection of the initial Learning Agreement returns the application to a state
where the student can edit its mapping and submit a new agreement. We still need
to decide whether to represent this using `created` or a separate
`la_rejected` status.

## 6. Decisions still to make

These points are not fully specified by the brief and should be decided before
the logical schema is finalized:

1. Can one user hold more than one role, or exactly one role?

2. Can the same student create multiple applications for the same academic year?
3. Can one foreign course map to multiple Ca' Foscari courses, and vice versa?
4. How should different grading systems be stored: free text, numeric values, or
   both?
5. Can office staff reopen a closed application?
6. Should partner institutions be deleted or only deactivated when already used?
7. Should status history and decision history be retained for auditing?

