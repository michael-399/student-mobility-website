// StudentDetailComponent – full read-only + action view of a single mobility application.
// Displays application metadata, learning agreements, exam mappings, and modification history.
// Provides context-sensitive actions based on the current application status:
// upload LA, set actual dates, propose modifications, mark ready for transcript, upload transcript with grades.
import { Component, OnInit, inject, ChangeDetectorRef } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe } from "@angular/common";
import { StudentService } from "../../../services/student.service";
import { FormsModule } from "@angular/forms";

@Component({
  selector: "app-student-detail",
  standalone: true,
  imports: [RouterLink, DatePipe, FormsModule],
  templateUrl: "./detail.html",
  styleUrl: "./detail.css",
})
export class StudentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private svc = inject(StudentService);
  private cdr = inject(ChangeDetectorRef);

  // The loaded application object (null while loading)
  app: any = null;
  loading = true;
  error = "";

  // Learning Agreement upload state
  laFile: File | null = null;
  laMsg = "";

  // Actual arrival/departure date editing state
  arrival = "";
  departure = "";
  datesMsg = "";

  // Modification proposal state
  modFile: File | null = null;
  modDesc = "";
  modMsg = "";
  modExamMappings: { foreignTeachingCode: string; foreignCourseName: string; foreignCredits: number; localCourseCode: string; localCourseName: string; localCredits: number }[] = [];

  // Transcript of Records upload state
  toFile: File | null = null;
  toMsg = "";
  // Per-exam grade entries for transcript submission
  examScores: { examMappingIndex: number; score: string; examDate: string }[] = [];

  // Ready-for-transcript action feedback
  readyMsg = "";

  // Human-readable labels for the expectedPeriod enum
  periodLabel: Record<string, string> = {
    first_semester: "First Semester",
    second_semester: "Second Semester",
    entire_year: "Entire Academic Year",
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

  // Fetch application by route :id parameter
  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get("id")!;
    this.svc.getById(id).subscribe({
      next: (data) => {
        this.app = data;
        this.loading = false;
        // Pre-populate date inputs (strip time component for <input type="date">)
        if (data.actualArrivalDate) this.arrival = data.actualArrivalDate.slice(0, 10);
        if (data.actualDepartureDate) this.departure = data.actualDepartureDate.slice(0, 10);
        this.cdr.detectChanges();
      },
      error: () => {
        this.error = "Application not found";
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  // Trigger browser download of a specific Learning Agreement file by index
  downloadLA(index: number) {
    this.svc.downloadLA(this.app._id, index).subscribe({
      next: (res) => {
        const filename = this.app.learningAgreements?.[index]?.fileName ?? "learning-agreement";
        const url = window.URL.createObjectURL(res.body!);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: () => (this.laMsg = "Download failed"),
    });
  }

  // Capture LA file from file input
  onLAFile(e: Event) {
    this.laFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  // Check if any LA is currently pending lecturer evaluation
  hasPendingLA(): boolean {
    return this.app?.learningAgreements?.some((la: any) => la.status === "pending") ?? false;
  }

  // Check if any modification proposal is currently pending evaluation
  hasPendingModification(): boolean {
    return this.app?.modifications?.some((m: any) => m.status === "pending") ?? false;
  }

  // Upload a new Learning Agreement (multipart)
  uploadLA() {
    if (!this.laFile) return;
    this.svc.uploadLA(this.app._id, this.laFile).subscribe({
      next: (data) => {
        this.app = data;
        this.laMsg = "Learning Agreement uploaded";
        this.laFile = null;
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.laMsg = err.error?.error ?? "Upload failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Save actual arrival and departure dates (available during mobility)
  saveDates() {
    this.svc.setDates(this.app._id, { actualArrivalDate: this.arrival, actualDepartureDate: this.departure }).subscribe({
      next: (data) => {
        this.app = data;
        this.datesMsg = "Dates saved";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.datesMsg = err.error?.error ?? "Failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Capture modification proposal file from file input
  onModFile(e: Event) {
    this.modFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  // Populate the mod exam mapping editor from the current application mappings
  loadModExamMappings() {
    this.modExamMappings = this.app.examMappings.map((m: any) => ({ ...m }));
  }

  // Add a blank row to the modification exam mapping editor
  addModRow() {
    this.modExamMappings.push({ foreignTeachingCode: "", foreignCourseName: "", foreignCredits: 6, localCourseCode: "", localCourseName: "", localCredits: 6 });
  }

  // Remove an exam mapping row from the modification editor
  removeModRow(i: number) {
    if (this.modExamMappings.length > 1) {
      this.modExamMappings.splice(i, 1);
    }
  }

  // Submit a modification proposal with the edited exam mappings
  submitMod() {
    if (!this.modFile || !this.modDesc) return;
    const validMappings = this.modExamMappings.filter(
      (m) => m.foreignTeachingCode && m.foreignCourseName && m.localCourseCode && m.localCourseName
    );
    if (validMappings.length === 0) return;
    this.svc
      .proposeModification(this.app._id, this.modFile, {
        description: this.modDesc,
        examMappingDiff: validMappings,
      })
      .subscribe({
        next: (data) => {
          this.app = data;
          this.modMsg = "Modification proposed";
          this.modFile = null;
          this.modDesc = "";
          this.modExamMappings = [];
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.modMsg = err.error?.error ?? "Failed";
          this.cdr.detectChanges();
        },
      });
  }

  // Mark the application as ready for transcript upload (transitions to "torUploaded" status)
  markReadyForTranscript() {
    this.svc.readyForTranscript(this.app._id).subscribe({
      next: (data) => {
        this.app = data;
        this.readyMsg = "Application marked as ready for transcript upload";
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.readyMsg = err.error?.error ?? "Failed";
        this.cdr.detectChanges();
      },
    });
  }

  // Capture Transcript of Records PDF file from file input
  onToFile(e: Event) {
    this.toFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  // Populate examScores array from the current exam mappings (one row per mapping)
  initExamScores() {
    this.examScores = this.app.examMappings.map((_: any, i: number) => ({
      examMappingIndex: i,
      score: "",
      examDate: "",
    }));
  }

  // Upload Transcript of Records PDF together with exam grades
  uploadToR() {
    if (!this.toFile) return;
    this.svc.uploadTranscript(this.app._id, this.toFile, this.examScores).subscribe({
      next: (data) => {
        this.app = data;
        this.toMsg = "Transcript uploaded";
        this.toFile = null;
        this.examScores = [];
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.toMsg = err.error?.error ?? "Failed";
        this.cdr.detectChanges();
      },
    });
  }
}
