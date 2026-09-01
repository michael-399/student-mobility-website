// StudentCreateComponent — form for starting a new mobility application.
//
// Creation now collects only the application itself: academic year, host
// institution, coordinator, expected period, and an optional note. The
// Learning Agreement and its course mappings are submitted afterwards
// from the detail page, because the backend models them as a version that
// the coordinator approves or rejects on its own.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink } from "@angular/router";
import { ReferenceService } from "../../../services/reference.service";
import { StudentService } from "../../../services/student.service";
import type { Institution, MobilityPeriod, User } from "../../../services/models";

@Component({
  selector: "app-student-create",
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: "./create.html",
})
export class StudentCreateComponent implements OnInit {
  private refSvc = inject(ReferenceService);
  private stuSvc = inject(StudentService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  institutions: Institution[] = [];
  coordinators: User[] = [];
  error = "";
  submitting = false;

  // Form model, bound via ngModel.
  academic_year = "2025/2026";
  host_institution_id: number | null = null;
  coordinator_id: number | null = null;
  expected_mobility_period: MobilityPeriod = "first_semester";
  optional_note = "";

  ngOnInit(): void {
    this.refSvc.listInstitutions().subscribe({
      next: (institutions) => {
        this.institutions = institutions;
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = "Failed to load institutions";
        this.cdr.detectChanges();
      },
    });
    this.refSvc.listCoordinators().subscribe({
      next: (coordinators) => {
        this.coordinators = coordinators;
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = "Failed to load coordinators";
        this.cdr.detectChanges();
      },
    });
  }

  canSubmit(): boolean {
    return Boolean(
      this.academic_year && this.host_institution_id && this.coordinator_id
    );
  }

  submit() {
    if (!this.canSubmit()) return;

    this.submitting = true;
    this.error = "";

    this.stuSvc
      .create({
        academic_year: this.academic_year,
        host_institution_id: this.host_institution_id!,
        coordinator_id: this.coordinator_id!,
        expected_mobility_period: this.expected_mobility_period,
        optional_note: this.optional_note || null,
      })
      .subscribe({
        // Straight to the detail page: the next thing to do is upload the
        // Learning Agreement, and that is where it happens.
        next: (app) => this.router.navigate(["/student", app.application_id]),
        error: (err) => {
          this.error = err.error?.error ?? "Failed to create application";
          this.submitting = false;
          this.cdr.detectChanges();
        },
      });
  }
}
