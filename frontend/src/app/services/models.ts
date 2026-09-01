// models.ts — Shapes returned by the Flask API, plus the display labels
// that go with them.
//
// The API speaks snake_case with integer ids. Enum values are the strings
// the backend stores, so they are matched exactly; the labels here are the
// only place they are turned into English.

export type Role = "student" | "coordinator" | "office_staff";

export interface User {
  user_id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
}

export interface Institution {
  institution_id: number;
  name: string;
  country: string;
  city: string;
  contact_email: string | null;
  is_active: boolean;
}

export type RecognitionStatus = "pending" | "approved" | "rejected";

export interface ExamResult {
  result_id: number;
  mapping_id: number;
  foreign_grade: string;
  exam_date: string | null;
  recognition_status: RecognitionStatus;
  decision_date: string | null;
  rejection_reason: string | null;
}

export interface CourseMapping {
  mapping_id: number;
  home_course_code: string;
  home_course_name: string;
  home_course_credits: number;
  foreign_course_code: string;
  foreign_course_name: string;
  foreign_course_credits: number;
  exam_result: ExamResult | null;
}

export type ApprovalStatus = "pending" | "approved" | "rejected";

// A Learning Agreement version. A revision proposed during the mobility
// is simply the next version, so there is no separate "modification".
export interface LearningAgreement {
  version_number: number;
  uploaded_at: string | null;
  approval_status: ApprovalStatus;
  decision_date: string | null;
  rejection_reason: string | null;
  course_mappings: CourseMapping[];
}

export interface Transcript {
  transcript_id: number;
  uploaded_at: string | null;
}

export type ApplicationStatus =
  | "created"
  | "waiting_la_approval"
  | "pre_departure_completed"
  | "mobility_in_progress"
  | "under_exam_recognition"
  | "closed";

export interface StatusChange {
  old_status: ApplicationStatus | null;
  new_status: ApplicationStatus;
  changed_at: string | null;
}

export type MobilityPeriod = "first_semester" | "second_semester" | "full_year";

// The summary form, returned by the list endpoints.
export interface Application {
  application_id: number;
  academic_year: string;
  optional_note: string | null;
  expected_mobility_period: MobilityPeriod;
  status: ApplicationStatus;
  student: User;
  academic_coordinator: User;
  host_institution: Institution;
  actual_arrival_date: string | null;
  actual_departure_date: string | null;
}

// The full aggregate, returned by every single-application endpoint.
export interface ApplicationDetail extends Application {
  learning_agreements: LearningAgreement[];
  transcript: Transcript | null;
  status_history: StatusChange[];
}

// A course mapping as it is entered in the form, before the server
// assigns it an id.
export interface CourseMappingInput {
  home_course_code: string;
  home_course_name: string;
  home_course_credits: number;
  foreign_course_code: string;
  foreign_course_name: string;
  foreign_course_credits: number;
}

export function emptyCourseMapping(): CourseMappingInput {
  return {
    home_course_code: "",
    home_course_name: "",
    home_course_credits: 6,
    foreign_course_code: "",
    foreign_course_name: "",
    foreign_course_credits: 6,
  };
}

export function isCompleteMapping(mapping: CourseMappingInput): boolean {
  return Boolean(
    mapping.home_course_code &&
      mapping.home_course_name &&
      mapping.foreign_course_code &&
      mapping.foreign_course_name &&
      mapping.home_course_credits > 0 &&
      mapping.foreign_course_credits > 0
  );
}

export const PERIOD_LABEL: Record<MobilityPeriod, string> = {
  first_semester: "First Semester",
  second_semester: "Second Semester",
  full_year: "Full Year",
};

export const STATUS_LABEL: Record<ApplicationStatus, string> = {
  created: "Draft",
  waiting_la_approval: "Awaiting LA Approval",
  pre_departure_completed: "Pre-departure Complete",
  mobility_in_progress: "Mobility in Progress",
  under_exam_recognition: "Exam Recognition",
  closed: "Closed",
};

export const APPROVAL_LABEL: Record<ApprovalStatus, string> = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
};

export function fullName(user: User | null | undefined): string {
  return user ? `${user.first_name} ${user.last_name}` : "";
}

// The highest approved Learning Agreement is the mapping in force: an
// approved revision supersedes earlier versions, a rejected one does not.
export function currentAgreement(
  application: ApplicationDetail | null
): LearningAgreement | null {
  const approved = (application?.learning_agreements ?? []).filter(
    (agreement) => agreement.approval_status === "approved"
  );

  if (approved.length === 0) {
    return null;
  }

  return approved.reduce((latest, agreement) =>
    agreement.version_number > latest.version_number ? agreement : latest
  );
}

export function pendingAgreement(
  application: ApplicationDetail | null
): LearningAgreement | null {
  return (
    (application?.learning_agreements ?? []).find(
      (agreement) => agreement.approval_status === "pending"
    ) ?? null
  );
}
