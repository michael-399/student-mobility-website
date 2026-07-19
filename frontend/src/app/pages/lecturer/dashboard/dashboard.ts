// Lecturer Dashboard Component
// Displays all mobility applications assigned to the currently logged-in lecturer.
// Provides a read-only overview with links to the detail view for evaluation.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { LecturerService } from "../../../services/lecturer.service";

@Component({
  selector: "app-lecturer-dashboard",
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: "./dashboard.html",
  styleUrl: "./dashboard.css",
})
export class LecturerDashboardComponent implements OnInit {
  // Inject the lecturer API service and Angular change detector
  private svc = inject(LecturerService);
  private cdr = inject(ChangeDetectorRef);

  // Component state
  apps: any[] = [];
  loading = true;
  error = "";

  // Maps API period keys to human-readable labels for the table
  periodLabel: Record<string, string> = {
    first_semester: "1st Semester",
    second_semester: "2nd Semester",
    entire_year: "Full Year",
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

  // Fetch the list of applications assigned to this lecturer on init
  ngOnInit(): void {
    this.svc.list().subscribe({
      next: (data) => {
        // Guard against non-array responses
        this.apps = Array.isArray(data) ? data : [];
        this.loading = false;
        this.cdr.detectChanges(); // Trigger manual change detection in OnPush components
      },
      error: (err) => {
        // Extract the most descriptive error message available
        this.error = err.error?.error ?? err.statusText ?? "Failed to load applications";
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }
}
