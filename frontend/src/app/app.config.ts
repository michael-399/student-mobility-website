// app.config.ts — Application-wide configuration.
// Declares the providers that Angular needs at bootstrap:
//   - Router (with the lazy-loaded route map)
//   - HTTP client (with the auth interceptor that attaches JWT tokens)
//   - Global error listener (for unhandled errors in the browser)

import { ApplicationConfig, provideBrowserGlobalErrorListeners } from "@angular/core";
import { provideRouter } from "@angular/router";
import { provideHttpClient, withInterceptors } from "@angular/common/http";
import { routes } from "./app.routes";
import { authInterceptor } from "./services/auth.interceptor";

export const appConfig: ApplicationConfig = {
  providers: [
    // Logs unhandled errors that bubble up out of the Angular zone.
    provideBrowserGlobalErrorListeners(),
    // Registers the application's route definitions.
    provideRouter(routes),
    // Provides HttpClient and attaches the JWT auth interceptor to every request.
    provideHttpClient(withInterceptors([authInterceptor])),
  ],
};
