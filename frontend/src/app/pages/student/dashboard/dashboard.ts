// StudentDashboardComponent – lists all mobility applications for the logged-in student.
// Provides a table view with status badges, action buttons (view/delete/cancel), and a link to create new applications.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { StudentService } from "../../../services/student.service";

@Component({
  selector: "app-student-dashboard",
  standalone: true,
  imports: [RouterLink, DatePipe],
  templateUrl: "./dashboard.html",
  styleUrl: "./dashboard.css",
})
export class StudentDashboardComponent implements OnInit {
  private svc = inject(StudentService);
  // ChangeDetectorRef is needed because we mutate arrays in-place on cancel
  private cdr = inject(ChangeDetectorRef);

  // All student applications loaded from the backend
  apps: any[] = [];
  loading = true;

  // Human-readable labels for the expectedPeriod enum values
  periodLabel: Record<string, string> = {
    first_semester: "1st Semester",
    second_semester: "2nd Semester",
    entire_year: "Full Year",
  };

  // Human-readable labels for application statuses
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

  error = "";

  // Fetch all applications on component initialization
  ngOnInit(): void {
    this.svc.list().subscribe({
      next: (data) => {
        this.apps = Array.isArray(data) ? data : [];
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error("Failed to load applications", err);
        this.error = err.error?.error ?? err.statusText ?? "Failed to load applications";
        this.apps = [];
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  // Delete an application permanently (only available for non-closed apps)
  deleteApp(id: string) {
    if (!confirm("Delete this application?")) return;
    this.svc.delete(id).subscribe(() => {
      this.apps = this.apps.filter((a) => a._id !== id);
      this.cdr.detectChanges();
    });
  }

  // Cancel an application – sets its status to "canceled" without deleting it
  cancelApp(id: string) {
    if (!confirm("Cancel this application? This cannot be undone.")) return;
    this.svc.cancelApplication(id).subscribe(() => {
      const app = this.apps.find((a) => a._id === id);
      if (app) {
        app.status = "canceled";
        this.cdr.detectChanges();
      }
    });
  }
}
