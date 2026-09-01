// coordinator.service.ts — Academic coordinator API calls.
//
// Replaces the previous lecturer service. Two endpoints are gone because
// the backend no longer models them separately: evaluating a
// "modification" is just deciding the next Learning Agreement version,
// and an exam grade is decided by its own result id rather than by an
// index into an array.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { map } from "rxjs";
import type { Application, ApplicationDetail, ExamResult } from "./models";

export type Decision = "approved" | "rejected";

@Injectable({ providedIn: "root" })
export class CoordinatorService {
  private http = inject(HttpClient);
  private base = "/api/coordinator";

  list() {
    return this.http
      .get<{ applications: Application[] }>(`${this.base}/applications`)
      .pipe(map((res) => res.applications));
  }

  getById(id: number | string) {
    return this.http
      .get<{ application: ApplicationDetail }>(`${this.base}/applications/${id}`)
      .pipe(map((res) => res.application));
  }

  downloadLearningAgreement(id: number | string, versionNumber: number) {
    return this.http.get(
      `${this.base}/applications/${id}/learning-agreements/${versionNumber}/file`,
      { responseType: "blob", observe: "response" }
    );
  }

  downloadTranscript(id: number | string) {
    return this.http.get(`${this.base}/applications/${id}/transcript/file`, {
      responseType: "blob",
      observe: "response",
    });
  }

  // Decides the version awaiting a decision. A rejection must carry a
  // reason; the server refuses one without.
  decideLearningAgreement(
    id: number | string,
    decision: Decision,
    reason?: string
  ) {
    return this.http
      .post<{ application: ApplicationDetail }>(
        `${this.base}/applications/${id}/learning-agreement/decision`,
        { decision, reason: reason ?? null }
      )
      .pipe(map((res) => res.application));
  }

  decideExamResult(resultId: number, decision: Decision, reason?: string) {
    return this.http
      .post<{ exam_result: ExamResult }>(
        `${this.base}/exam-results/${resultId}/decision`,
        { decision, reason: reason ?? null }
      )
      .pipe(map((res) => res.exam_result));
  }
}
