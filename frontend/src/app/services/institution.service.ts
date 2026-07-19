// institution.service.ts — Lookup service for shared reference data.
// Provides lists of partner institutions and referent lecturers that
// are used across student, lecturer, and office views (e.g. dropdowns).

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";

// A partner (host) institution where students can go on exchange.
export interface Institution {
  _id: string;
  name: string;
  country: string;
  city: string;
}

// A referent lecturer who can validate Learning Agreements and scores.
export interface Lecturer {
  _id: string;
  name: string;
  email: string;
}

@Injectable({ providedIn: "root" })
export class InstitutionService {
  private http = inject(HttpClient);

  // Returns all partner institutions known to the system.
  listInstitutions() {
    return this.http.get<Institution[]>("/api/institutions");
  }

  // Returns all referent lecturers — used to populate lecturer selectors.
  listLecturers() {
    return this.http.get<Lecturer[]>("/api/lecturers");
  }
}
