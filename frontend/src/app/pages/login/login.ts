// login.ts — Login page component.
// Handles email/password authentication and role-based redirect
// after a successful login. Uses template-driven forms (FormsModule).

import { Component, inject, ChangeDetectorRef } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router } from "@angular/router";
import { AuthService } from "../../services/auth.service";

@Component({
  selector: "app-login",
  standalone: true,
  imports: [FormsModule],
  templateUrl: "./login.html",
  styleUrl: "./login.css",
})
export class LoginComponent {
  // Service dependencies injected via the inject() function.
  private auth = inject(AuthService);
  private router = inject(Router);
  // ChangeDetectorRef is used to manually trigger change detection
  // after an async error, ensuring the error message appears in the UI.
  private cdr = inject(ChangeDetectorRef);

  // Two-way bound to the email and password input fields via ngModel.
  email = "";
  password = "";
  // Displayed below the form when login fails.
  error = "";
  // Disables the submit button and shows a spinner while the request is in flight.
  loading = false;

  // Called on form submit (ngSubmit).
  submit(): void {
    // Client-side validation — fail fast before making a network call.
    if (!this.email || !this.password) {
      this.error = "Email and password are required";
      return;
    }

    this.loading = true;
    this.error = "";

    // Call the auth service; on success, route the user to their
    // role-specific dashboard. On failure, show the server error.
    this.auth.login(this.email, this.password).subscribe({
      next: (res) => {
        this.loading = false;
        // Role-based redirect after successful login.
        if (res.user.role === "student") {
          this.router.navigate(["/student/dashboard"]);
        } else if (res.user.role === "lecturer") {
          this.router.navigate(["/lecturer/dashboard"]);
        } else {
          this.router.navigate(["/office/dashboard"]);
        }
      },
      error: (err) => {
        this.loading = false;
        // Use the server-provided error message if available; fallback to generic.
        this.error = err.error?.error ?? "Login failed";
        // Manually trigger change detection because the error may have been
        // set inside a callback where zone.js doesn't automatically detect it.
        this.cdr.detectChanges();
      },
    });
  }
}
