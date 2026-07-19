// auth.service.ts — Handles authentication (login/logout) and stores
// the JWT token + user object in the browser's localStorage so the
// interceptor can attach the token to outgoing requests and the UI
// can display the current user's info.

import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable, tap } from "rxjs";

// Shape of the response returned by POST /api/auth/login.
export interface LoginResponse {
  token: string;
  user: { id: string; email: string; name: string; role: string };
}

// Provided at root so a single instance is shared across the entire app.
@Injectable({ providedIn: "root" })
export class AuthService {
  private http = inject(HttpClient);
  // Keys used to persist auth data in localStorage.
  private tokenKey = "token";
  private userKey = "user";

  // Sends credentials to the API and, on success, saves the returned
  // JWT token and user profile to localStorage via the rxjs tap operator.
  login(email: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>("/api/auth/login", { email, password })
      .pipe(
        tap((res) => {
          localStorage.setItem(this.tokenKey, res.token);
          localStorage.setItem(this.userKey, JSON.stringify(res.user));
        })
      );
  }

  // Clears all persisted auth data (token + user).
  logout(): void {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
  }

  // Retrieves the raw JWT token string, or null if not logged in.
  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  // Parses and returns the stored user object, or null if none exists.
  getUser(): { id: string; email: string; name: string; role: string } | null {
    const raw = localStorage.getItem(this.userKey);
    return raw ? JSON.parse(raw) : null;
  }

  // Convenience check: truthy if a token is currently stored.
  isLoggedIn(): boolean {
    return !!this.getToken();
  }
}
