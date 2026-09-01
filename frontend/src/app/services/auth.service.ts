// auth.service.ts — Authentication against the Flask API.
//
// The session is a cookie the browser holds and the interceptor sends
// with every request; it is HttpOnly, so this code never sees it. The
// user object cached in localStorage is only for rendering the nav bar
// without a round trip — the cookie, not that cache, is what actually
// authenticates a request, and the server decides on every call.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable, tap } from "rxjs";
import type { User } from "./models";

export interface SessionResponse {
  user: User;
}

@Injectable({ providedIn: "root" })
export class AuthService {
  private http = inject(HttpClient);
  private userKey = "user";

  login(email: string, password: string): Observable<SessionResponse> {
    return this.http
      .post<SessionResponse>("/api/login", { email, password })
      .pipe(tap((res) => this.cacheUser(res.user)));
  }

  // Clears the server-side session, then the local cache. The cache is
  // cleared even if the call fails, so the UI never claims to be signed
  // in when the user has asked to leave.
  logout(): Observable<unknown> {
    return this.http
      .post("/api/logout", {})
      .pipe(tap({ next: () => this.clear(), error: () => this.clear() }));
  }

  // Re-reads the signed-in user from the server, refreshing the cache.
  me(): Observable<SessionResponse> {
    return this.http
      .get<SessionResponse>("/api/me")
      .pipe(tap((res) => this.cacheUser(res.user)));
  }

  getUser(): User | null {
    const raw = localStorage.getItem(this.userKey);

    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as User;
    } catch {
      // A corrupted cache should log the user out, not break the shell.
      this.clear();
      return null;
    }
  }

  // Whether the UI should render as signed in. The server still decides
  // every request; a stale cache resolves itself on the next 401.
  isLoggedIn(): boolean {
    return this.getUser() !== null;
  }

  clear(): void {
    localStorage.removeItem(this.userKey);
  }

  // The dashboard this user's role starts at.
  homePath(): string {
    switch (this.getUser()?.role) {
      case "student":
        return "/student/dashboard";
      case "coordinator":
        return "/coordinator/dashboard";
      case "office_staff":
        return "/office/dashboard";
      default:
        return "/login";
    }
  }

  private cacheUser(user: User): void {
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }
}
