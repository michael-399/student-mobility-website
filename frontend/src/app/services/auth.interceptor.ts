// auth.interceptor.ts — Sends the session cookie with every API call and
// handles the server rejecting it.
//
// There is no token to attach: authentication is an HttpOnly cookie the
// browser holds. What this must do is set `withCredentials`, which is
// what makes the browser include that cookie at all once the API is on a
// different origin.

import { HttpInterceptorFn, HttpErrorResponse } from "@angular/common/http";
import { catchError, throwError } from "rxjs";

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const withSession = req.clone({ withCredentials: true });

  return next(withSession).pipe(
    catchError((err: HttpErrorResponse) => {
      // A 401 means the session is gone or was never established. Drop the
      // cached user and send them to sign in again -- except on the login
      // call itself, where a 401 is just wrong credentials and the form
      // should show the message.
      if (err.status === 401 && !req.url.includes("/api/login")) {
        localStorage.removeItem("user");
        window.location.href = "/login";
      }

      return throwError(() => err);
    })
  );
};
