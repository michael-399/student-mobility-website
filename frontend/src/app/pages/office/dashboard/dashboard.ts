// OfficeDashboardComponent — every application in the system, with a
// status filter, for administrative oversight.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { RouterLink } from "@angular/router";
import { FormsModule } from "@angular/forms";
import { OfficeService } from "../../../services/office.service";
import {
  PERIOD_LABEL,
  STATUS_LABEL,
  type Application,
  type ApplicationStatus,
} from "../../../services/models";

@Component({
  selector: "app-office-dashboard",
  standalone: true,
  imports: [RouterLink, FormsModule],
  templateUrl: "./dashboard.html",
})
export class OfficeDashboardComponent implements OnInit {
  private svc = inject(OfficeService);
  private cdr = inject(ChangeDetectorRef);

  apps: Application[] = [];
  loading = true;
  error = "";

  // "" means no filter.
  statusFilter: ApplicationStatus | "" = "";

  periodLabel = PERIOD_LABEL;
  statusLabel = STATUS_LABEL;
  // Object.keys loses the key type, so the filter options are listed
  // explicitly and stay in workflow order.
  statuses: ApplicationStatus[] = [
    "created",
    "waiting_la_approval",
    "pre_departure_completed",
    "mobility_in_progress",
    "under_exam_recognition",
    "closed",
  ];

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.svc.list(this.statusFilter).subscribe({
      next: (apps) => {
        this.apps = apps;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = err.error?.error ?? err.statusText ?? "Failed to load applications";
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  // The two gates the office owns, so the queue is visible at a glance.
  needsAction(app: Application): boolean {
    return (
      app.status === "waiting_la_approval" ||
      app.status === "under_exam_recognition"
    );
  }
}
