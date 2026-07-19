// office.service.ts — HTTP service for mobility-office-facing API calls.
// The mobility office manages the overall workflow: moving applications
// to "in progress" (pre-departure), closing completed applications,
// and downloading Learning Agreements for audit purposes.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";

@Injectable({ providedIn: "root" })
export class OfficeService {
  private http = inject(HttpClient);
  // Base path for all office-facing application endpoints.
  private base = "/api/office/applications";

  // Fetch all applications visible to the mobility office.
  list() {
    return this.http.get<any[]>(this.base);
  }

  // Fetch a single application by its MongoDB _id.
  getById(id: string) {
    return this.http.get<any>(`${this.base}/${id}`);
  }

  // Mark an approved application as "in progress" (student is abroad).
  markInProgress(id: string) {
    return this.http.patch<any>(`${this.base}/${id}/pre-departure`, {});
  }

  // Close/finalise an application once the mobility period is complete.
  closeApplication(id: string) {
    return this.http.patch<any>(`${this.base}/${id}/close`, {});
  }

  // Download a specific version of the Learning Agreement as a blob.
  downloadLA(id: string, index: number) {
    return this.http.get(`${this.base}/${id}/learning-agreement/${index}/download`, {
      responseType: "blob",
      observe: "response",
    });
  }
}
