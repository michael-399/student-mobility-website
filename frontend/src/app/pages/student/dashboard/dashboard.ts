// StudentDashboardComponent — lists the signed-in student's applications.
// Table view with status badges and links into the detail page.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { RouterLink } from "@angular/router";
import { StudentService } from "../../../services/student.service";
import { PERIOD_LABEL, STATUS_LABEL, type Application } from "../../../services/models";

@Component({
  selector: "app-student-dashboard",
  standalone: true,
  imports: [RouterLink],
  templateUrl: "./dashboard.html",
})
export class StudentDashboardComponent implements OnInit {
  private svc = inject(StudentService);
  private cdr = inject(ChangeDetectorRef);

  apps: Application[] = [];
  loading = true;
  error = "";

  periodLabel = PERIOD_LABEL;
  statusLabel = STATUS_LABEL;

  ngOnInit(): void {
    this.svc.list().subscribe({
      next: (apps) => {
        this.apps = apps;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = err.error?.error ?? err.statusText ?? "Failed to load applications";
        this.apps = [];
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  // Only a draft can be withdrawn. Once submitted, an application is a
  // record of what happened and stays.
  canDelete(app: Application): boolean {
    return app.status === "created";
  }

  deleteApp(id: number) {
    if (!confirm("Delete this application?")) return;
    this.svc.delete(id).subscribe({
      next: () => {
        this.apps = this.apps.filter((a) => a.application_id !== id);
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.error = err.error?.error ?? "Failed to delete";
        this.cdr.detectChanges();
      },
    });
  }
}
