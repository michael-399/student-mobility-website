// StudentCreateComponent – form for creating a new student mobility application.
// Collects academic year, host institution, referent lecturer, expected period,
// exam mappings (course equivalences between home and host institutions), and the Learning Agreement PDF.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink } from "@angular/router";
import { InstitutionService, type Institution, type Lecturer } from "../../../services/institution.service";
import { StudentService } from "../../../services/student.service";

@Component({
  selector: "app-student-create",
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: "./create.html",
  styleUrl: "./create.css",
})
export class StudentCreateComponent implements OnInit {
  private instSvc = inject(InstitutionService);
  private stuSvc = inject(StudentService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  // Dropdown data loaded from the backend
  institutions: Institution[] = [];
  lecturers: Lecturer[] = [];
  error = "";
  submitting = false;

  // Form model fields – bound via ngModel in the template
  academicYear = "2025/2026";
  hostInstitutionId = "";
  referentLecturerId = "";
  expectedPeriod = "first_semester";

  // Exam mapping rows: each row maps a local course to a foreign (host) course
  examMappings = [{ foreignTeachingCode: "", foreignCourseName: "", foreignCredits: 6, localCourseCode: "", localCourseName: "", localCredits: 6 }];

  // Learning Agreement PDF file selected by the user
  laFile: File | null = null;

  // Load institutions and lecturers dropdowns on init (parallel requests)
  ngOnInit(): void {
    this.instSvc.listInstitutions().subscribe({
      next: (insts) => {
        this.institutions = insts;
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = "Failed to load institutions";
        this.cdr.detectChanges();
      },
    });
    this.instSvc.listLecturers().subscribe({
      next: (lecs) => {
        this.lecturers = lecs;
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = "Failed to load lecturers";
        this.cdr.detectChanges();
      },
    });
  }

  // Capture the Learning Agreement PDF file from the file input
  onLAFile(e: Event) {
    this.laFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  // Add a new empty exam mapping row
  addRow() {
    this.examMappings.push({ foreignTeachingCode: "", foreignCourseName: "", foreignCredits: 6, localCourseCode: "", localCourseName: "", localCredits: 6 });
  }

  // Remove an exam mapping row by index
  removeRow(i: number) {
    this.examMappings.splice(i, 1);
  }

  // Validate form: host + lecturer selected, LA file uploaded, at least one complete mapping
  canSubmit(): boolean {
    if (!this.hostInstitutionId || !this.referentLecturerId) return false;
    if (!this.laFile) return false;
    const validMappings = this.examMappings.filter(
      (m) => m.foreignTeachingCode && m.foreignCourseName && m.localCourseCode && m.localCourseName
    );
    return validMappings.length > 0;
  }

  // Submit the form: send all fields + LA file to the backend, then navigate to dashboard
  submit() {
    if (!this.canSubmit()) return;

    // Filter out incomplete mapping rows before sending
    const mappings = this.examMappings.filter(
      (m) => m.foreignTeachingCode && m.foreignCourseName && m.localCourseCode && m.localCourseName
    );

    this.submitting = true;
    this.error = "";

    // multipart/form-data: application JSON fields + the LA PDF file
    this.stuSvc
      .create({
        academicYear: this.academicYear,
        hostInstitutionId: this.hostInstitutionId,
        referentLecturerId: this.referentLecturerId,
        expectedPeriod: this.expectedPeriod,
        examMappings: mappings,
      }, this.laFile!)
      .subscribe({
        next: () => {
          // On success, redirect to the dashboard
          this.router.navigateByUrl("/student/dashboard", { skipLocationChange: false });
        },
        error: (err) => {
          this.error = err.error?.error ?? "Failed to create";
          this.submitting = false;
          this.cdr.detectChanges();
        },
      });
  }
}
