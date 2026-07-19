// lecturer.service.ts — HTTP service for lecturer-facing API calls.
// Lecturers can list assigned applications, download Learning Agreements,
// evaluate (approve/reject) LAs and modifications, and approve exam scores.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";

@Injectable({ providedIn: "root" })
export class LecturerService {
  private http = inject(HttpClient);
  // Base path for all lecturer application endpoints.
  private base = "/api/lecturer/applications";

  // Fetch all applications assigned to the authenticated lecturer.
  list() {
    return this.http.get<any[]>(this.base);
  }

  // Fetch a single application by its MongoDB _id.
  getById(id: string) {
    return this.http.get<any>(`${this.base}/${id}`);
  }

  // Download a specific version of the Learning Agreement as a blob.
  downloadLA(id: string, index: number) {
    return this.http.get(`${this.base}/${id}/learning-agreement/${index}/download`, {
      responseType: "blob",
      observe: "response",
    });
  }

  // Approve or reject a Learning Agreement. An optional free-text reason
  // can be provided (especially for rejections).
  evaluateLA(id: string, status: string, reason?: string) {
    return this.http.patch<any>(`${this.base}/${id}/learning-agreement/evaluate`, {
      status,
      // Map empty/undefined reason to undefined so the key is omitted.
      reason: reason ?? undefined,
    });
  }

  // Approve or reject a proposed LA modification.
  evaluateModification(id: string, modId: string, status: string, reason?: string) {
    return this.http.patch<any>(`${this.base}/${id}/modifications/${modId}/evaluate`, {
      status,
      reason: reason ?? undefined,
    });
  }

  // Approve an individual exam score on the transcript (by its index).
  approveScore(id: string, scoreIndex: number) {
    return this.http.patch<any>(`${this.base}/${id}/transcript/scores/${scoreIndex}`, {});
  }
}
