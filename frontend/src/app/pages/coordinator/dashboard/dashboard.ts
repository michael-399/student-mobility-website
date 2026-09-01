// CoordinatorDashboardComponent — applications assigned to the signed-in
// academic coordinator, with the ones awaiting a decision called out.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { RouterLink } from "@angular/router";
import { CoordinatorService } from "../../../services/coordinator.service";
import { PERIOD_LABEL, STATUS_LABEL, type Application } from "../../../services/models";

@Component({
  selector: "app-coordinator-dashboard",
  standalone: true,
  imports: [RouterLink],
  templateUrl: "./dashboard.html",
})
export class CoordinatorDashboardComponent implements OnInit {
  private svc = inject(CoordinatorService);
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
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  // The summary list carries no agreements, so "needs me" is read from
  // the status rather than by inspecting versions.
  awaitingDecision(app: Application): boolean {
    return app.status === "waiting_la_approval";
  }
}
