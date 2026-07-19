# student-mobility-website

# Overseas Mobility Management Platform - Project Plan

## Phase 0: Setup & Environment (1-2 days)

| Task ID | Task Description | Type |
|---------|------------------|------|
| S01 | Set up Flask project structure (`app/` folder, `config.py`, `requirements.txt`, `run.py`) | Backend |
| S02 | Initialize PostgreSQL database and configure SQLAlchemy connection | Backend |
| S03 | Set up Flask-Migrate for schema versioning | Backend |
| S04 | Configure environment variables (`.env`) for secrets | Backend |
| S05 | Set up basic HTML template with navigation bar (Bootstrap 5) | Frontend |

---

## Phase 1: Database Design (2-3 days)

| Task ID | Task Description | Type |
|---------|------------------|------|
| D01 | Create conceptual ER diagram (documentation) | Both |
| D02 | Define SQLAlchemy models: `User` (polymorphic roles), `HostInstitution` | Backend |
| D03 | Define models: `MobilityApplication` (with status field and constraints) | Backend |
| D04 | Define models: `ExamMapping` (foreign ↔ Ca' Foscari courses) | Backend |
| D05 | Define models: `LearningAgreement` (file reference, version, approval status) | Backend |
| D06 | Define models: `LearningAgreementModification` (for change proposals) | Backend |
| D07 | Define models: `TranscriptOfRecords` (file reference, upload date) | Backend |
| D08 | Define models: `ExamResult` (grade, date passed, recognition status) | Backend |
| D09 | Define enums for `ApplicationStatus`, `ApprovalStatus`, `MobilityPeriod` | Backend |
| D10 | Set up foreign key relationships and cascade behaviors | Backend |
| D11 | Write database seed script with sample users, institutions, applications | Backend |

---

## Phase 2: Authentication & Role Management (2 days)

| Task ID | Task Description | Type |
|---------|------------------|------|
| A01 | Implement user registration (student only, via form) | Full Stack |
| A02 | Implement login/logout using Flask-Login | Full Stack |
| A03 | Create role-based decorators (`@student_required`, `@coordinator_required`, `@office_required`) | Backend |
| A04 | Build user profile page (view/edit own info) | Full Stack |
| A05 | Create admin interface for Overseas office to create coordinator accounts | Full Stack |

---

## Phase 3: Core CRUD & Workflow (4-5 days)

### 3.1 Host Institution Management

| Task ID | Task Description | Type |
|---------|------------------|------|
| H01 | List all host institutions (read-only for students) | Full Stack |
| H02 | Overseas office: add/edit/delete institutions | Full Stack |

### 3.2 Mobility Application Creation

| Task ID | Task Description | Type |
|---------|------------------|------|
| M01 | Create form for new application (academic year, host institution, period, coordinator) | Full Stack |
| M02 | Backend validation: prevent duplicate active applications per student | Backend |
| M03 | List student's own applications with status badges | Full Stack |
| M04 | Detail view for a single application (shows all related data) | Full Stack |

### 3.3 Exam Mapping (within application)

| Task ID | Task Description | Type |
|---------|------------------|------|
| M05 | Form to add/edit exam mappings (6 fields from spec) | Full Stack |
| M06 | Display exam mappings table in application detail view | Frontend |
| M07 | Prevent exam mapping edits when status = `waiting_LA_approval` or beyond (unless rejected) | Backend |

### 3.4 Learning Agreement Upload & Approval

| Task ID | Task Description | Type |
|---------|------------------|------|
| LA01 | File upload form for Learning Agreement (store file path/URL) | Full Stack |
| LA02 | Coordinator view: list applications assigned to them | Full Stack |
| LA03 | Coordinator: view LA file, approve/reject with motivation and date | Full Stack |
| LA04 | Update application status after approval (→ `pre_departure_pending`) | Backend |
| LA05 | Update application status after rejection (→ `created`) | Backend |

### 3.5 Pre-departure Check (Overseas Office)

| Task ID | Task Description | Type |
|---------|------------------|------|
| O01 | Office dashboard: list all applications with filters | Full Stack |
| O02 | Office: mark pre-departure as complete (only if LA approved) | Full Stack |
| O03 | Update status to `pre_departure_completed` | Backend |

---

## Phase 4: Mobility In Progress (2-3 days)

| Task ID | Task Description | Type |
|---------|------------------|------|
| P01 | Student: enter/edit actual arrival/departure dates (only when status = `pre_departure_completed`) | Full Stack |
| P02 | Student: propose modification to exam mappings + upload new LA version | Full Stack |
| P03 | Coordinator: view pending modifications, approve/reject with motivation | Full Stack |
| P04 | On rejection: restore previous exam mappings automatically | Backend |
| P05 | Update status to `mobility_in_progress` after arrival date entered | Backend |

---

## Phase 5: After Return & Exam Recognition (2-3 days)

| Task ID | Task Description | Type |
|---------|------------------|------|
| R01 | Student: upload Transcript of Records file | Full Stack |
| R02 | Student: for each exam mapping, enter grade and date passed | Full Stack |
| R03 | Coordinator: view submitted grades, approve/reject each exam individually | Full Stack |
| R04 | Track recognition status per exam (pending/approved/rejected) | Backend |
| R05 | Office: close application (only if all exams have recognition decision) | Full Stack |

---

## Phase 6: Advanced Features (3 days - Recommended)

| Task ID | Task Description | Type | Priority |
|---------|------------------|------|----------|
| AD01 | File version history for Learning Agreement (keep old files) | Backend | Medium |
| AD02 | Index on `(application.status, application.academic_year)` for dashboard performance | Backend | Medium |
| AD03 | Implement database transactions for approval/rejection workflows | Backend | High |
| AD04 | Add soft delete for applications (`is_active` flag) | Backend | Low |
| AD05 | Dashboard charts for Office (applications by status/country) | Frontend | Low |
| AD06 | Email notifications on status changes (using Flask-Mail) | Backend | Low |
| AD07 | Materialized view for "incomplete applications" report | Backend | Low |

---

## Phase 7: Documentation & Polish (2-3 days)

| Task ID | Task Description | Type |
|---------|------------------|------|
| DOC01 | Write introduction and main functionalities (report section 1-2) | Both |
| DOC02 | Document conceptual and logical design with diagrams (section 3) | Both |
| DOC03 | Document main SQL queries used in the app (section 4) | Backend |
| DOC04 | Document integrity policies, security, indexes (section 5) | Both |
| DOC05 | Document tech stack and libraries (section 6) | Backend |
| DOC06 | Write appendix with individual contributions (section 7) | Both |
| DOC07 | Add code comments throughout | Both |
| DOC08 | Prepare live demo script and test all workflows | Both |

---

## Suggested Task Assignment (3 people)

| Person | Focus Areas | Task IDs |
|--------|-------------|----------|
| **A** | Backend & Database | S01-S04, D01-D11, A03, M02, LA04-LA05, P04-P05, R04-R05, AD02-AD04, DOC04 |
| **B** | Frontend & UI | S05, H01, M03-M04, M06, LA02, O01, P01, R02, AD06, DOC01-DOC02 |
| **C** | Full Stack (Forms & Workflows) | A01-A02, A04-A05, M01, M05, M07, LA01, LA03, O02-O03, P02-P03, R01, R03, AD01, AD05, DOC03, DOC05-DOC08 |

---

## Milestones

| Milestone | Deadline (approx.) | Deliverables |
|-----------|-------------------|---------------|
| Milestone 1 | End of Week 1 | Database schema, models, seed data |
| Milestone 2 | End of Week 2 | Authentication, application creation, LA upload/approval |
| Milestone 3 | End of Week 3 | Full workflow (departure → mobility → return → recognition) |
| Milestone 4 | End of Week 4 | Advanced features, documentation, demo ready |
