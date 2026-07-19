// main.ts — Angular application entry point.
// Bootstraps the root component (App) using the app configuration
// that wires up the router, HTTP client, and auth interceptor.

import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

// Start the application with the root component and its providers.
// Any bootstrap error is logged to the console for debugging.
bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
