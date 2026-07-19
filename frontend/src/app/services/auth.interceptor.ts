// auth.interceptor.ts — Functional HTTP interceptor that attaches a
// Bearer token to every outgoing request (when available) and handles
// 401 responses by clearing stored auth data and redirecting to login.

import { HttpInterceptorFn, HttpErrorResponse } from "@angular/common/http";
import { catchError, throwError } from "rxjs";

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Read the JWT token from localStorage (set by AuthService on login).
  const token = localStorage.getItem("token");
  if (token) {
    // Clone the request and attach the Authorization header.
    const cloned = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
    return next(cloned).pipe(
      catchError((err: HttpErrorResponse) => {
        // If the server responds with 401 for a non-login request,
        // the token is expired/invalid — clear storage and redirect.
        if (err.status === 401 && !req.url.includes("/auth/login")) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          window.location.href = "/login";
        }
        // Re-throw the error so callers (e.g. components) can handle it.
        return throwError(() => err);
      })
    );
  }
  // No token available — forward the request unchanged.
  return next(req);
};
