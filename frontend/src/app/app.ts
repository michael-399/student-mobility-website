// app.ts — Root application component.
// Provides the router outlet for page content and the logout action.

import { Component, inject } from "@angular/core";
import { RouterOutlet, RouterLink } from "@angular/router";
import { AuthService } from "./services/auth.service";
import { fullName } from "./services/models";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  templateUrl: "./app.html",
  styleUrl: "./app.css",
})
export class App {
  auth = inject(AuthService);

  // Shown in the nav bar. The API returns names in two parts.
  get displayName(): string {
    return fullName(this.auth.getUser());
  }

  // Ends the server-side session before leaving, so the cookie is not
  // left valid on the server after the user has signed out.
  logout() {
    this.auth.logout().subscribe({
      next: () => (window.location.href = "/login"),
      error: () => (window.location.href = "/login"),
    });
  }
}
