// app.ts — Root application component.
// Serves as the shell for the entire SPA. It provides a router outlet
// for page content and a logout action accessible from the layout.

import { Component, inject } from "@angular/core";
import { RouterOutlet, RouterLink } from "@angular/router";
import { AuthService } from "./services/auth.service";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  templateUrl: "./app.html",
  styleUrl: "./app.css",
})
export class App {
  // Inject the auth service to access logout functionality and user state.
  auth = inject(AuthService);

  // Clears auth data from local storage and redirects to the login page.
  logout() {
    this.auth.logout();
    window.location.href = "/login";
  }
}
