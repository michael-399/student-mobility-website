// Office Application Detail Component
// Loads a single student mobility application by route ID for administrative review.
// Office staff can view all application data (read-only) and perform state transitions:
// - Mark pre-departure applications as "in progress"
// - Close applications that have reached the score-approval stage
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { OfficeService } from "../../../services/office.service";

@Component({
  selector: "app-office-detail",
  standalone: true,
  imports: [RouterLink, DatePipe], // No FormsModule needed; office has no text inputs
  templateUrl: "./detail.html",
  styleUrl: "./detail.css",
})
export class OfficeDetailComponent implements OnInit {
  // Inject route (to read the :id param), API service, and change detector
  private route = inject(ActivatedRoute);
  private svc = inject(OfficeService);
  private cdr = inject(ChangeDetectorRef);

  // Application data and UI state
  app: any = null;
  loading = true;
  error = "";
  actionMsg = "";  // Feedback message shown after administrative actions

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

  // Constructs a display name for an exam by looking up its mapping
  getExamName(index: number): string {
    const mapping = this.app?.examMappings?.[index];
    return mapping ? `${mapping.foreignCourseName} (${mapping.localCourseName})` : "Unknown";
  }

  // Transition the application from "preDepartureDone" to "inProgress"
  markInProgress() {
    this.svc.markInProgress(this.app._id).subscribe({
      next: (data) => {
        this.app = data;          // Replace with updated application from server
        this.actionMsg = "Application marked as in progress";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.actionMsg = err.error?.error ?? "Action failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Close the application (final state transition, irreversible)
  // Prompts for confirmation before proceeding
  closeApplication() {
    if (!confirm("Close this application? This cannot be undone.")) return;
    this.svc.closeApplication(this.app._id).subscribe({
      next: (data) => {
        this.app = data;
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
