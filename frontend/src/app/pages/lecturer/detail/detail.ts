// Lecturer Application Detail Component
// Loads a single student mobility application by route ID and allows the lecturer to:
// - Download and evaluate Learning Agreements (approve/reject)
// - Evaluate proposed modifications to the application
// - Approve individual exam scores
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { LecturerService } from "../../../services/lecturer.service";

@Component({
  selector: "app-lecturer-detail",
  standalone: true,
  imports: [RouterLink, DatePipe, FormsModule], // FormsModule needed for [(ngModel)] on textareas
  templateUrl: "./detail.html",
  styleUrl: "./detail.css",
})
export class LecturerDetailComponent implements OnInit {
  // Inject route (to read the :id param), API service, and change detector
  private route = inject(ActivatedRoute);
  private svc = inject(LecturerService);
  private cdr = inject(ChangeDetectorRef);

  // Application data and UI state
  app: any = null;
  loading = true;
  error = "";

  // Two-way bound form fields for Learning Agreement evaluation
  reasonLA = "";   // Rejection reason (required when rejecting)
  evalMsg = "";    // Feedback message shown after approve/reject

  // Two-way bound form fields for Modification evaluation
  reasonMod = "";  // Rejection reason (required when rejecting)
  evalModMsg = ""; // Feedback message shown after approve/reject

  // Feedback message for score approval actions
  scoreMsg = "";

  // Maps API period keys to human-readable labels
  periodLabel: Record<string, string> = {
    first_semester: "First Semester",
    second_semester: "Second Semester",
    entire_year: "Entire Academic Year",
  };

  // Maps API status keys to human-readable labels for the status badge
  statusLabel: Record<string, string> = {
    created: "Created",
    awaitingLA: "Awaiting LA Approval",
    "needs modifications": "Needs Modifications",
    preDepartureDone: "Pre-departure Done",
    inProgress: "Mobility in Progress",
    torUploaded: "Waiting for Score Approval",
    closed: "Closed",
    canceled: "Canceled",
  };

  // Extract the application ID from the route and fetch its full data
  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get("id")!;
    this.svc.getById(id).subscribe({
      next: (data) => {
        this.app = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = "Application not found";
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  // Returns true if at least one Learning Agreement has status "pending"
  hasPendingLA(): boolean {
    return this.app?.learningAgreements?.some((la: any) => la.status === "pending");
  }

  // Returns true if at least one Modification has status "pending"
  hasPendingModification(): boolean {
    return this.app?.modifications?.some((m: any) => m.status === "pending");
  }

  // Returns the _id of the first pending modification, or empty string if none
  getFirstPendingModId(): string {
    return this.app?.modifications?.find((m: any) => m.status === "pending")?._id ?? "";
  }

  // Returns true if at least one ExamScore has status "pending"
  hasPendingScores(): boolean {
    return this.app?.examScores?.some((s: any) => s.status === "pending");
  }

  // Constructs a display name for an exam by looking up its mapping
  getExamName(index: number): string {
    const mapping = this.app?.examMappings?.[index];
    return mapping ? `${mapping.foreignCourseName} (${mapping.localCourseName})` : "Unknown";
  }

  // Triggers a browser download of a Learning Agreement file by index
  downloadLA(index: number) {
    this.svc.downloadLA(this.app._id, index).subscribe({
      next: (res) => {
        const filename = this.app.learningAgreements?.[index]?.fileName ?? "learning-agreement";
        // Create a temporary download link from the blob response
        const url = window.URL.createObjectURL(res.body!);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url); // Clean up the object URL
      },
    });
  }

  // Approve the pending Learning Agreement
  approveLA() {
    this.svc.evaluateLA(this.app._id, "approved").subscribe({
      next: (data) => {
        this.app = data;          // Replace with updated application from server
        this.evalMsg = "Learning Agreement approved";
        this.reasonLA = "";       // Clear the rejection reason field
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.evalMsg = err.error?.error ?? "Evaluation failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Reject the pending Learning Agreement (requires a reason)
  rejectLA() {
    if (!this.reasonLA) return;   // Guard: reason is mandatory for rejection
    this.svc.evaluateLA(this.app._id, "rejected", this.reasonLA).subscribe({
      next: (data) => {
        this.app = data;
        this.evalMsg = "Learning Agreement rejected";
        this.reasonLA = "";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.evalMsg = err.error?.error ?? "Evaluation failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Approve a pending modification by its ID
  approveModification(modId: string) {
    this.svc.evaluateModification(this.app._id, modId, "approved").subscribe({
      next: (data) => {
        this.app = data;
        this.evalModMsg = "Modification approved";
        this.reasonMod = "";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.evalModMsg = err.error?.error ?? "Evaluation failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Reject a pending modification by its ID (requires a reason)
  rejectModification(modId: string) {
    if (!this.reasonMod) return;  // Guard: reason is mandatory for rejection
    this.svc.evaluateModification(this.app._id, modId, "rejected", this.reasonMod).subscribe({
      next: (data) => {
        this.app = data;
        this.evalModMsg = "Modification rejected";
        this.reasonMod = "";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.evalModMsg = err.error?.error ?? "Evaluation failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Approve an exam score by its index in the examScores array
  approveScore(scoreIndex: number) {
    this.svc.approveScore(this.app._id, scoreIndex).subscribe({
      next: (data) => {
        this.app = data;
        this.scoreMsg = "Score approved";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.scoreMsg = err.error?.error ?? "Approval failed";
        this.cdr.detectChanges();
      },
    });
  }
}
