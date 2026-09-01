// office.service.ts — Overseas office API calls.
//
// The office sees every application and owns the two administrative
// gates: signing off the pre-departure check, and closing the application
// once every exam has been decided.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { map } from "rxjs";
import type {
  Application,
  ApplicationDetail,
  ApplicationStatus,
  Institution,
} from "./models";

@Injectable({ providedIn: "root" })
export class OfficeService {
  private http = inject(HttpClient);
  private base = "/api/office";

  list(status?: ApplicationStatus | "") {
    const query = status ? `?status=${status}` : "";

    return this.http
      .get<{ applications: Application[] }>(`${this.base}/applications${query}`)
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

  // Signs off the pre-departure check. The mobility itself begins when
  // the student reports arriving.
  completePreDeparture(id: number | string) {
    return this.http
      .post<{ application: ApplicationDetail }>(
        `${this.base}/applications/${id}/pre-departure`,
        {}
      )
      .pipe(map((res) => res.application));
  }

  closeApplication(id: number | string) {
    return this.http
      .post<{ application: ApplicationDetail }>(
        `${this.base}/applications/${id}/close`,
        {}
      )
      .pipe(map((res) => res.application));
  }

  listInstitutions(includeInactive = false) {
    const query = includeInactive ? "?include_inactive=true" : "";

    return this.http
      .get<{ institutions: Institution[] }>(`${this.base}/institutions${query}`)
      .pipe(map((res) => res.institutions));
  }

  createInstitution(data: {
    name: string;
    country: string;
    city: string;
    contact_email?: string | null;
  }) {
    return this.http
      .post<{ institution: Institution }>(`${this.base}/institutions`, data)
      .pipe(map((res) => res.institution));
  }

  // Partners are retired, never deleted: existing applications must keep
  // pointing at the institution they were made for.
  deactivateInstitution(id: number) {
    return this.http
      .post<{ institution: Institution }>(
        `${this.base}/institutions/${id}/deactivate`,
        {}
      )
      .pipe(map((res) => res.institution));
  }

  reactivateInstitution(id: number) {
    return this.http
      .post<{ institution: Institution }>(
        `${this.base}/institutions/${id}/reactivate`,
        {}
      )
      .pipe(map((res) => res.institution));
  }
}
