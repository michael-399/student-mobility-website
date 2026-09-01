// student.service.ts — Student-facing API calls.
//
// Two shape changes from the previous backend are worth knowing:
//
//  * Creating an application no longer carries a file or course mappings.
//    It is plain JSON; the Learning Agreement and its mappings are
//    submitted afterwards, as a version.
//  * There is no separate "propose modification" call. A revision is the
//    next Learning Agreement version, so `submitLearningAgreement` serves
//    the first submission, a resubmission after rejection, and a
//    mid-mobility revision alike.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { map } from "rxjs";
import type {
  Application,
  ApplicationDetail,
  CourseMappingInput,
  MobilityPeriod,
} from "./models";

export interface ApplicationInput {
  academic_year: string;
  host_institution_id: number;
  expected_mobility_period: MobilityPeriod;
  coordinator_id: number;
  optional_note?: string | null;
}

export interface ExamResultInput {
  mapping_id: number;
  foreign_grade: string;
  exam_date: string;
}

@Injectable({ providedIn: "root" })
export class StudentService {
  private http = inject(HttpClient);
  private base = "/api/student/applications";

  list() {
    return this.http
      .get<{ applications: Application[] }>(this.base)
      .pipe(map((res) => res.applications));
  }

  getById(id: number | string) {
    return this.http
      .get<{ application: ApplicationDetail }>(`${this.base}/${id}`)
      .pipe(map((res) => res.application));
  }

  create(data: ApplicationInput) {
    return this.http
      .post<{ application: ApplicationDetail }>(this.base, data)
      .pipe(map((res) => res.application));
  }

  update(id: number | string, changes: Partial<ApplicationInput>) {
    return this.http
      .patch<{ application: ApplicationDetail }>(`${this.base}/${id}`, changes)
      .pipe(map((res) => res.application));
  }

  delete(id: number | string) {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  // Submits the next Learning Agreement version with its course mappings.
  submitLearningAgreement(
    id: number | string,
    file: File,
    mappings: CourseMappingInput[]
  ) {
    const form = new FormData();
    form.append("file", file);
    // A complex array cannot ride in multipart on its own, so it travels
    // as a JSON field alongside the file.
    form.append("course_mappings", JSON.stringify(mappings));

    return this.http
      .post<{ application: ApplicationDetail }>(
        `${this.base}/${id}/learning-agreements`,
        form
      )
      .pipe(map((res) => res.application));
  }

  downloadLearningAgreement(id: number | string, versionNumber: number) {
    return this.http.get(
      `${this.base}/${id}/learning-agreements/${versionNumber}/file`,
      { responseType: "blob", observe: "response" }
    );
  }

  // Recording the arrival is what starts the mobility.
  setMobilityDates(
    id: number | string,
    dates: { actual_arrival_date?: string; actual_departure_date?: string }
  ) {
    return this.http
      .patch<{ application: ApplicationDetail }>(
        `${this.base}/${id}/mobility-dates`,
        dates
      )
      .pipe(map((res) => res.application));
  }

  // Uploading the transcript opens exam recognition.
  uploadTranscript(id: number | string, file: File) {
    const form = new FormData();
    form.append("file", file);

    return this.http
      .post<{ application: ApplicationDetail }>(
        `${this.base}/${id}/transcript`,
        form
      )
      .pipe(map((res) => res.application));
  }

  downloadTranscript(id: number | string) {
    return this.http.get(`${this.base}/${id}/transcript/file`, {
      responseType: "blob",
      observe: "response",
    });
  }

  recordExamResults(id: number | string, results: ExamResultInput[]) {
    return this.http
      .put<{ application: ApplicationDetail }>(
        `${this.base}/${id}/exam-results`,
        { exam_results: results }
      )
      .pipe(map((res) => res.application));
  }
}
