// app.routes.ts — Route definitions for the application.
// All components are loaded lazily via dynamic imports to keep the
// initial bundle small. Routes are grouped by role (student, lecturer,
// office) plus a shared login page.

import { Routes } from "@angular/router";

export const routes: Routes = [
  // Public login page — no auth guard, accessible to everyone.
  { path: "login", loadComponent: () => import("./pages/login/login").then((m) => m.LoginComponent) },
  // Student role routes (lazy-loaded standalone components).
  {
    path: "student",
    loadComponent: () => import("./pages/student/dashboard/dashboard").then((m) => m.StudentDashboardComponent),
    pathMatch: "full",
  },
  {
    path: "student/dashboard",
    loadComponent: () => import("./pages/student/dashboard/dashboard").then((m) => m.StudentDashboardComponent),
  },
  {
    path: "student/create",
    loadComponent: () => import("./pages/student/create/create").then((m) => m.StudentCreateComponent),
  },
  {
    path: "student/:id",
    loadComponent: () => import("./pages/student/detail/detail").then((m) => m.StudentDetailComponent),
  },
  // Lecturer role routes.
  {
    path: "lecturer/dashboard",
    loadComponent: () => import("./pages/lecturer/dashboard/dashboard").then((m) => m.LecturerDashboardComponent),
  },
  {
    path: "lecturer/:id",
    loadComponent: () => import("./pages/lecturer/detail/detail").then((m) => m.LecturerDetailComponent),
  },
  // Office role routes.
  {
    path: "office/dashboard",
    loadComponent: () => import("./pages/office/dashboard/dashboard").then((m) => m.OfficeDashboardComponent),
  },
  {
    path: "office/:id",
    loadComponent: () => import("./pages/office/detail/detail").then((m) => m.OfficeDetailComponent),
  },
  // Default/empty path redirects to the login page.
  { path: "", redirectTo: "/login", pathMatch: "full" },
];
