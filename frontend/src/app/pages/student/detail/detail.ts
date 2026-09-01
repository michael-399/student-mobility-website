// StudentDetailComponent — the full view of one application, plus every
// action the student can take on it.
//
// Uploading a Learning Agreement and proposing a modification are now one
// operation: each submission is the next version, whether it is the first
// one, a resubmission after a rejection, or a revision during the
// mobility. The mappings editor is therefore shared by all three cases,
// and seeds itself from whichever version is currently in force.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { StudentService, type ExamResultInput } from "../../../services/student.service";
import { saveResponseAsFile } from "../../../services/download";
import {
  APPROVAL_LABEL,
  PERIOD_LABEL,
  STATUS_LABEL,
  currentAgreement,
  emptyCourseMapping,
  isCompleteMapping,
  pendingAgreement,
  type ApplicationDetail,
  type CourseMappingInput,
  type LearningAgreement,
} from "../../../services/models";

@Component({
  selector: "app-student-detail",
  standalone: true,
  imports: [RouterLink, DatePipe, FormsModule],
  templateUrl: "./detail.html",
})
export class StudentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private svc = inject(StudentService);
  private cdr = inject(ChangeDetectorRef);

  app: ApplicationDetail | null = null;
  loading = true;
  error = "";

  // Learning Agreement submission state.
  laFile: File | null = null;
  laMappings: CourseMappingInput[] = [];
  laMsg = "";

  // Mobility dates state.
  arrival = "";
  departure = "";
  datesMsg = "";

  // Transcript state.
  transcriptFile: File | null = null;
  transcriptMsg = "";

  // Exam results state, one row per mapping in the agreement in force.
  examResults: ExamResultInput[] = [];
  resultsMsg = "";

  periodLabel = PERIOD_LABEL;
  statusLabel = STATUS_LABEL;
  approvalLabel = APPROVAL_LABEL;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get("id")!;
    this.svc.getById(id).subscribe({
      next: (app) => {
        this.apply(app);
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = err.error?.error ?? "Application not found";
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  private apply(app: ApplicationDetail): void {
    this.app = app;
    // <input type="date"> needs a bare YYYY-MM-DD.
    this.arrival = app.actual_arrival_date ?? "";
    this.departure = app.actual_departure_date ?? "";
  }

  // ---- Learning Agreement -------------------------------------------------

  get agreements(): LearningAgreement[] {
    return this.app?.learning_agreements ?? [];
  }

  get currentAgreement(): LearningAgreement | null {
    return currentAgreement(this.app);
  }

  get pendingAgreement(): LearningAgreement | null {
    return pendingAgreement(this.app);
  }

  // A new version can be submitted while the application is a draft, or
  // during the mobility as a revision -- but never while one is already
  // awaiting a decision.
  canSubmitAgreement(): boolean {
    if (!this.app || this.pendingAgreement) return false;

    return this.app.status === "created" || this.app.status === "mobility_in_progress";
  }

  // The heading changes because the same form means different things: a
  // first submission, a corrected one, or a mid-mobility revision.
  get agreementFormTitle(): string {
    if (this.agreements.length === 0) return "Upload Learning Agreement";

    return this.app?.status === "mobility_in_progress"
      ? "Propose a Revised Learning Agreement"
      : "Upload a New Learning Agreement Version";
  }

  // Seeds the editor from the version in force, so a revision starts from
  // the approved mapping rather than a blank slate.
  startAgreement(): void {
    const source = this.currentAgreement;

    this.laMappings = source
      ? source.course_mappings.map((mapping) => ({
          home_course_code: mapping.home_course_code,
          home_course_name: mapping.home_course_name,
          home_course_credits: mapping.home_course_credits,
          foreign_course_code: mapping.foreign_course_code,
          foreign_course_name: mapping.foreign_course_name,
          foreign_course_credits: mapping.foreign_course_credits,
        }))
      : [emptyCourseMapping()];
  }

  addMappingRow(): void {
    this.laMappings.push(emptyCourseMapping());
  }

  removeMappingRow(index: number): void {
    this.laMappings.splice(index, 1);
  }

  onAgreementFile(event: Event): void {
    this.laFile = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  private completeMappings(): CourseMappingInput[] {
    return this.laMappings.filter(isCompleteMapping);
  }

  canSendAgreement(): boolean {
    return Boolean(this.laFile) && this.completeMappings().length > 0;
  }

  submitAgreement(): void {
    if (!this.app || !this.canSendAgreement()) return;

    this.svc
      .submitLearningAgreement(
        this.app.application_id,
        this.laFile!,
        this.completeMappings()
      )
      .subscribe({
        next: (app) => {
          this.apply(app);
          this.laMsg = "Learning Agreement submitted for approval";
          this.laFile = null;
          this.laMappings = [];
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.laMsg = err.error?.error ?? "Submission failed";
          this.cdr.detectChanges();
        },
      });
  }

  downloadAgreement(versionNumber: number): void {
    if (!this.app) return;

    this.svc
      .downloadLearningAgreement(this.app.application_id, versionNumber)
      .subscribe({
        next: (res) =>
          saveResponseAsFile(res, `learning-agreement-v${versionNumber}.pdf`),
        error: () => {
          this.laMsg = "Download failed";
          this.cdr.detectChanges();
        },
      });
  }

  // ---- Mobility dates -----------------------------------------------------

  // Recording the arrival is what starts the mobility, so the form opens
  // as soon as the office has signed off the pre-departure check.
  canEditDates(): boolean {
    return (
      this.app?.status === "pre_departure_completed" ||
      this.app?.status === "mobility_in_progress"
    );
  }

  saveDates(): void {
    if (!this.app) return;

    this.svc
      .setMobilityDates(this.app.application_id, {
        actual_arrival_date: this.arrival || undefined,
        actual_departure_date: this.departure || undefined,
      })
      .subscribe({
        next: (app) => {
          this.apply(app);
          this.datesMsg = "Dates saved";
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.datesMsg = err.error?.error ?? "Failed to save dates";
          this.cdr.detectChanges();
        },
      });
  }

  // ---- Transcript ---------------------------------------------------------

  canUploadTranscript(): boolean {
    return this.app?.status === "mobility_in_progress";
  }

  onTranscriptFile(event: Event): void {
    this.transcriptFile = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  uploadTranscript(): void {
    if (!this.app || !this.transcriptFile) return;

    this.svc
      .uploadTranscript(this.app.application_id, this.transcriptFile)
      .subscribe({
        next: (app) => {
          this.apply(app);
          this.transcriptMsg = "Transcript uploaded — exam recognition can begin";
          this.transcriptFile = null;
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.transcriptMsg = err.error?.error ?? "Upload failed";
          this.cdr.detectChanges();
        },
      });
  }

  downloadTranscript(): void {
    if (!this.app) return;

    this.svc.downloadTranscript(this.app.application_id).subscribe({
      next: (res) => saveResponseAsFile(res, "transcript-of-records.pdf"),
      error: () => {
        this.transcriptMsg = "Download failed";
        this.cdr.detectChanges();
      },
    });
  }

  // ---- Exam results -------------------------------------------------------

  canRecordResults(): boolean {
    return this.app?.status === "under_exam_recognition";
  }

  // One row per mapping in the agreement in force, pre-filled with any
  // grade already recorded.
  startExamResults(): void {
    const agreement = this.currentAgreement;

    this.examResults = (agreement?.course_mappings ?? []).map((mapping) => ({
      mapping_id: mapping.mapping_id,
      foreign_grade: mapping.exam_result?.foreign_grade ?? "",
      exam_date: mapping.exam_result?.exam_date ?? "",
    }));
  }

  // A grade the coordinator has already decided is no longer editable.
  isResultDecided(mappingId: number): boolean {
    const mapping = this.currentAgreement?.course_mappings.find(
      (m) => m.mapping_id === mappingId
    );

    return Boolean(
      mapping?.exam_result && mapping.exam_result.recognition_status !== "pending"
    );
  }

  courseNameFor(mappingId: number): string {
    const mapping = this.currentAgreement?.course_mappings.find(
      (m) => m.mapping_id === mappingId
    );

    return mapping
      ? `${mapping.foreign_course_name} → ${mapping.home_course_name}`
      : "Unknown course";
  }

  submitExamResults(): void {
    if (!this.app) return;

    // Only send rows the student filled in and the coordinator has not
    // already decided; the server rejects a change to a decided result.
    const results = this.examResults.filter(
      (row) =>
        row.foreign_grade && row.exam_date && !this.isResultDecided(row.mapping_id)
    );

    if (results.length === 0) {
      this.resultsMsg = "Enter a grade and date for at least one exam";
      return;
    }

    this.svc.recordExamResults(this.app.application_id, results).subscribe({
      next: (app) => {
        this.apply(app);
        this.resultsMsg = "Exam results submitted for recognition";
        this.examResults = [];
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.resultsMsg = err.error?.error ?? "Failed to submit results";
        this.cdr.detectChanges();
      },
    });
  }
}
