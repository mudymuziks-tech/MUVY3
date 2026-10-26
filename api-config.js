// MUVY API CONFIGURATION
// ---------------------------------------------------------------------------
// Single source of truth for the backend base URL used by the recognition
// feature (recognize.js).
//
// HOW IT WORKS
//   recognize.js:getApiBaseUrl() resolves the backend in this order:
//     1. window.MUVY_API_BASE_URL  (set below)
//     2. a global API_BASE_URL, if defined elsewhere
//     3. http://127.0.0.1:8000     (only when the page is served from
//                                   localhost / 127.0.0.1)
//
//   If none of these produce a URL, recognition is disabled and the UI shows
//   "Movie identification service is not configured."
//
// TO CONNECT A DEPLOYED BACKEND
//   Set DEPLOYED_API_BASE_URL below to your backend origin, with no trailing
//   slash. Example:
//     const DEPLOYED_API_BASE_URL = 'https://your-api.onrender.com';
//
//   Leave it as an empty string ('') to keep the current behaviour (localhost
//   default during local development; recognition disabled elsewhere).
// ---------------------------------------------------------------------------

(function configureMuvyApi() {
  // >>> SET YOUR DEPLOYED BACKEND ORIGIN HERE (leave '' when not deployed) <<<
  const DEPLOYED_API_BASE_URL = '';

  if (DEPLOYED_API_BASE_URL) {
    // Normalise: strip any trailing slashes so `${base}/identify` stays valid.
    window.MUVY_API_BASE_URL = DEPLOYED_API_BASE_URL.replace(/\/+$/, '');
  }
})();