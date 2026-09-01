// Dev-server proxy: forwards the app's /api calls to the Flask backend.
//
// Only /api is proxied, which is why the backend mounts its blueprints
// there: the SPA itself navigates to /student/... and /office/..., and
// those paths must keep reaching the Angular router.
//
// 127.0.0.1 rather than "localhost": on macOS "localhost" resolves to ::1
// first, where the AirPlay Receiver answers and returns 403.
const target = process.env["API_PROXY_TARGET"] || "http://127.0.0.1:5001";

module.exports = {
  "/api": {
    target,
    secure: false,
  },
};
