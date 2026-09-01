// CoordinatorDetailComponent — reviewing and deciding one application.
//
// Two decisions live here: the Learning Agreement version awaiting a
// decision, and each proposed exam recognition. There is no separate
// "modification" decision any more — a revision is simply the next
// version, so approving it is the same action as approving the first one.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { CoordinatorService } from "../../../services/coordinator.service";
import { saveResponseAsFile } from "../../../services/download";
import {
  APPROVAL_LABEL,
  PERIOD_LABEL,
  STATUS_LABEL,
  currentAgreement,
  pendingAgreement,
  type ApplicationDetail,
  type CourseMapping,
  type LearningAgreement,
} from "../../../services/models";

@Component({
  selector: "app-coordinator-detail",
  standalone: true,
  imports: [RouterLink, DatePipe, FormsModule],
  templateUrl: "./detail.html",
})
export class CoordinatorDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private svc = inject(CoordinatorService);
  private cdr = inject(ChangeDetectorRef);

  app: ApplicationDetail | null = null;
  loading = true;
  error = "";

  // Rejection reasons. The server requires one, and refuses the decision
  // without it, so the button stays disabled until it is filled in.
  laReason = "";
  laMsg = "";

  resultReasons: Record<number, string> = {};
  resultMsg = "";

  periodLabel = PERIOD_LABEL;
  statusLabel = STATUS_LABEL;
  approvalLabel = APPROVAL_LABEL;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get("id")!;
    this.svc.getById(id).subscribe({
      next: (app) => {
        this.app = app;
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

  get agreements(): LearningAgreement[] {
    return this.app?.learning_agreements ?? [];
  }

  get pendingAgreement(): LearningAgreement | null {
    return pendingAgreement(this.app);
  }

  get currentAgreement(): LearningAgreement | null {
    return currentAgreement(this.app);
  }

  // A revision proposed mid-mobility reads differently from a first
  // submission, and the coordinator should know which one they are on.
  get isRevision(): boolean {
    return this.agreements.length > 1;
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

  downloadTranscript(): void {
    if (!this.app) return;

    this.svc.downloadTranscript(this.app.application_id).subscribe({
      next: (res) => saveResponseAsFile(res, "transcript-of-records.pdf"),
      error: () => {
        this.resultMsg = "Download failed";
        this.cdr.detectChanges();
      },
    });
  }

  approveAgreement(): void {
    this.decideAgreement("approved");
  }

  rejectAgreement(): void {
    if (!this.laReason.trim()) return;

    this.decideAgreement("rejected", this.laReason);
  }

  private decideAgreement(decision: "approved" | "rejected", reason?: string): void {
    if (!this.app) return;

    this.svc
      .decideLearningAgreement(this.app.application_id, decision, reason)
      .subscribe({
        next: (app) => {
          this.app = app;
          this.laMsg =
            decision === "approved"
              ? "Learning Agreement approved"
              : "Learning Agreement rejected — returned to the student";
          this.laReason = "";
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.laMsg = err.error?.error ?? "Decision failed";
          this.cdr.detectChanges();
        },
      });
  }

  // Exam recognition only applies to the mapping currently in force.
  get recognitionMappings(): CourseMapping[] {
    return this.currentAgreement?.course_mappings ?? [];
  }

  hasPendingResults(): boolean {
    return this.recognitionMappings.some(
      (mapping) => mapping.exam_result?.recognition_status === "pending"
    );
  }

  approveResult(resultId: number): void {
    this.decideResult(resultId, "approved");
  }

  rejectResult(resultId: number): void {
    const reason = (this.resultReasons[resultId] ?? "").trim();

    if (!reason) return;

    this.decideResult(resultId, "rejected", reason);
  }

  private decideResult(
    resultId: number,
    decision: "approved" | "rejected",
    reason?: string
  ): void {
    if (!this.app) return;

    this.svc.decideExamResult(resultId, decision, reason).subscribe({
      // The response carries only the decided result, so the application
      // is re-read to refresh the status and every other row with it.
      next: () => {
        this.resultMsg = `Exam recognition ${decision}`;
        this.resultReasons[resultId] = "";
        this.reload();
      },
      error: (err) => {
        this.resultMsg = err.error?.error ?? "Decision failed";
        this.cdr.detectChanges();
      },
    });
  }

  private reload(): void {
    if (!this.app) return;

    this.svc.getById(this.app.application_id).subscribe({
      next: (app) => {
        this.app = app;
        this.cdr.detectChanges();
      },
    });
  }
}
