// MUVY API CONFIGURATION
// ---------------------------------------------------------------------------
// Local development:
//   Uses http://127.0.0.1:8000 when the frontend runs on localhost.
//
// Production:
//   Set DEPLOYED_API_BASE_URL to the correct deployed backend origin.
//   Leave it empty until the production backend is ready.
// ---------------------------------------------------------------------------

(function configureMuvyApi() {
  const localHosts = ['localhost', '127.0.0.1'];

  // Add the verified Render backend URL here after deployment.
  const DEPLOYED_API_BASE_URL = '';

  if (DEPLOYED_API_BASE_URL) {
    window.MUVY_API_BASE_URL =
      DEPLOYED_API_BASE_URL.replace(/\/+$/, '');
    return;
  }

  if (localHosts.includes(window.location.hostname)) {
    window.MUVY_API_BASE_URL = 'http://127.0.0.1:8000';
  }
})();