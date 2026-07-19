// Office Dashboard Component
// Displays all mobility applications in the system for administrative oversight.
// The office role can view every application and transition pre-departure applications
// to "in progress" directly from the dashboard.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { OfficeService } from "../../../services/office.service";

@Component({
  selector: "app-office-dashboard",
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: "./dashboard.html",
  styleUrl: "./dashboard.css",
})
export class OfficeDashboardComponent implements OnInit {
  // Inject the office API service and Angular change detector
  private svc = inject(OfficeService);
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

  // Fetch all applications in the system on init
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
