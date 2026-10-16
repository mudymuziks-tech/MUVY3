// Override MUVY_API_BASE_URL before this script to use another API service.
const localHosts = ['localhost', '127.0.0.1'];
window.MUVY_API_BASE_URL = window.MUVY_API_BASE_URL || (
  localHosts.includes(window.location.hostname)
    ? 'http://127.0.0.1:8000'
    : 'https://muvy3.onrender.com'
);