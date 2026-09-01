// app.routes.ts — Route definitions.
// All components are loaded lazily to keep the initial bundle small.
// Routes are grouped by role (student, coordinator, office) plus a shared
// login page.

import { Routes } from "@angular/router";

export const routes: Routes = [
  // Public login page — accessible to everyone.
  { path: "login", loadComponent: () => import("./pages/login/login").then((m) => m.LoginComponent) },
  // Student role routes.
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
  // Academic coordinator routes.
  {
    path: "coordinator/dashboard",
    loadComponent: () => import("./pages/coordinator/dashboard/dashboard").then((m) => m.CoordinatorDashboardComponent),
  },
  {
    path: "coordinator/:id",
    loadComponent: () => import("./pages/coordinator/detail/detail").then((m) => m.CoordinatorDetailComponent),
  },
  // Overseas office routes.
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
