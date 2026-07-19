// student.service.ts — HTTP service for all student-facing API calls.
// Covers CRUD on mobility applications, file uploads/downloads,
// date management, modification proposals, and transcript submission.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";

@Injectable({ providedIn: "root" })
export class StudentService {
  private http = inject(HttpClient);
  // Base path for all student application endpoints.
  private base = "/api/student/applications";

  // Fetch all applications belonging to the authenticated student.
  list() {
    return this.http.get<any[]>(this.base);
  }

  // Fetch a single application by its MongoDB _id.
  getById(id: string) {
    return this.http.get<any>(`${this.base}/${id}`);
  }

  // Create a new mobility application. The supporting document (PDF/CV/etc.)
  // is sent as multipart/form-data alongside the structured fields.
  create(data: any, file: File) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("academicYear", data.academicYear);
    fd.append("hostInstitutionId", data.hostInstitutionId);
    fd.append("expectedPeriod", data.expectedPeriod);
    fd.append("referentLecturerId", data.referentLecturerId);
    // examMappings is a complex array — serialise to JSON for transport.
    fd.append("examMappings", JSON.stringify(data.examMappings));
    return this.http.post<any>(this.base, fd);
  }

  // Hard-delete an application (only allowed for draft/pending applications).
  delete(id: string) {
    return this.http.delete<any>(`${this.base}/${id}`);
  }

  // Cancel (soft-delete) an application that has already been submitted.
  cancelApplication(id: string) {
    return this.http.patch<any>(`${this.base}/${id}/cancel`, {});
  }

  // Upload a Learning Agreement PDF for a specific application.
  uploadLA(id: string, file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return this.http.post<any>(`${this.base}/${id}/learning-agreement`, fd);
  }

  // Download a specific version of the Learning Agreement as a blob
  // (used to trigger a browser file-save dialog).
  downloadLA(id: string, index: number) {
    return this.http.get(`${this.base}/${id}/learning-agreement/${index}/download`, {
      responseType: "blob",
      observe: "response",
    });
  }

  // Set actual arrival/departure dates on an approved application.
  setDates(id: string, data: { actualArrivalDate?: string; actualDepartureDate?: string }) {
    return this.http.patch<any>(`${this.base}/${id}/dates`, data);
  }

  // Propose a modification to the Learning Agreement (e.g. change an exam).
  proposeModification(id: string, file: File, data: { description: string; examMappingDiff: any[] }) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("description", data.description);
    // Diff describing which exam mappings to add/remove/change.
    fd.append("examMappingDiff", JSON.stringify(data.examMappingDiff));
    return this.http.post<any>(`${this.base}/${id}/modifications`, fd);
  }

  // Mark the application as ready for transcript submission.
  readyForTranscript(id: string) {
    return this.http.patch<any>(`${this.base}/${id}/ready-for-transcript`, {});
  }

  // Upload the final transcript PDF with per-exam scores and dates.
  uploadTranscript(id: string, file: File, examScores: { examMappingIndex: number; score: string; examDate: string }[]) {
    const fd = new FormData();
    fd.append("file", file);
    // Serialise the array of exam score objects into a single JSON field.
    fd.append("examScores", JSON.stringify(examScores));
    return this.http.post<any>(`${this.base}/${id}/transcript`, fd);
  }
}
