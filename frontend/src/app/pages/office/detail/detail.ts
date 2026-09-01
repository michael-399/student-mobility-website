// OfficeDetailComponent — administrative view of one application.
//
// The office owns two gates: signing off the pre-departure check once the
// coordinator has approved a Learning Agreement, and closing the
// application once every submitted exam has been decided. Everything else
// here is read-only.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { OfficeService } from "../../../services/office.service";
import { saveResponseAsFile } from "../../../services/download";
import {
  APPROVAL_LABEL,
  PERIOD_LABEL,
  STATUS_LABEL,
  currentAgreement,
  type ApplicationDetail,
  type CourseMapping,
  type LearningAgreement,
} from "../../../services/models";

@Component({
  selector: "app-office-detail",
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: "./detail.html",
})
export class OfficeDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private svc = inject(OfficeService);
  private cdr = inject(ChangeDetectorRef);

  app: ApplicationDetail | null = null;
  loading = true;
  error = "";
  actionMsg = "";

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

  get currentAgreement(): LearningAgreement | null {
    return currentAgreement(this.app);
  }

  get recognitionMappings(): CourseMapping[] {
    return this.currentAgreement?.course_mappings ?? [];
  }

  // Requires an approved agreement, which the server checks too; showing
  // the button only when it can succeed avoids an error the user cannot act on.
  canCompletePreDeparture(): boolean {
    return (
      this.app?.status === "waiting_la_approval" && this.currentAgreement !== null
    );
  }

  canClose(): boolean {
    if (this.app?.status !== "under_exam_recognition") return false;
    if (!this.app.transcript) return false;

    const results = this.recognitionMappings
      .map((mapping) => mapping.exam_result)
      .filter((result) => result !== null);

    return (
      results.length > 0 &&
      results.every((result) => result!.recognition_status !== "pending")
    );
  }

  // Why the close button is not available yet, so the office is not left
  // guessing what it is waiting on.
  get closeBlockedReason(): string {
    if (this.app?.status !== "under_exam_recognition") {
      return "Available once the transcript has been uploaded.";
    }

    const results = this.recognitionMappings
      .map((mapping) => mapping.exam_result)
      .filter((result) => result !== null);

    if (results.length === 0) {
      return "Waiting for the student to submit exam results.";
    }

    if (results.some((result) => result!.recognition_status === "pending")) {
      return "Waiting for the coordinator to decide every exam recognition.";
    }

    return "";
  }

  downloadAgreement(versionNumber: number): void {
    if (!this.app) return;

    this.svc
      .downloadLearningAgreement(this.app.application_id, versionNumber)
      .subscribe({
        next: (res) =>
          saveResponseAsFile(res, `learning-agreement-v${versionNumber}.pdf`),
        error: () => {
          this.actionMsg = "Download failed";
          this.cdr.detectChanges();
        },
      });
  }

  downloadTranscript(): void {
    if (!this.app) return;

    this.svc.downloadTranscript(this.app.application_id).subscribe({
      next: (res) => saveResponseAsFile(res, "transcript-of-records.pdf"),
      error: () => {
        this.actionMsg = "Download failed";
        this.cdr.detectChanges();
      },
    });
  }

  completePreDeparture(): void {
    if (!this.app) return;

    this.svc.completePreDeparture(this.app.application_id).subscribe({
      next: (app) => {
        this.app = app;
        this.actionMsg =
          "Pre-departure check complete — the mobility starts when the student records their arrival";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.actionMsg = err.error?.error ?? "Action failed";
        this.cdr.detectChanges();
      },
    });
  }

  closeApplication(): void {
    if (!this.app) return;
    if (!confirm("Close this application? It cannot be modified afterwards.")) return;

    this.svc.closeApplication(this.app.application_id).subscribe({
      next: (app) => {
        this.app = app;
        this.actionMsg = "Application closed";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.actionMsg = err.error?.error ?? "Action failed";
        this.cdr.detectChanges();
      },
    });
  }
}
