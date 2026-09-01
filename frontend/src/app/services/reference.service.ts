// reference.service.ts — Lookup data shared by every role: the partner
// institutions a student may choose from, and the coordinators who can be
// assigned to an application.
//
// The API returns only active institutions here, so a retired partner
// stops being selectable without affecting existing applications.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { map } from "rxjs";
import type { Institution, User } from "./models";

@Injectable({ providedIn: "root" })
export class ReferenceService {
  private http = inject(HttpClient);

  listInstitutions() {
    return this.http
      .get<{ institutions: Institution[] }>("/api/reference/institutions")
      .pipe(map((res) => res.institutions));
  }

  listCoordinators() {
    return this.http
      .get<{ coordinators: User[] }>("/api/reference/coordinators")
      .pipe(map((res) => res.coordinators));
  }
}
