const BASE_URL = 'https://7fe038f5dcfd.ngrok-free.app/pypikachu'
const fetchInit = {
  headers: {'ngrok-skip-browser-warning': 'true'},
  credentials: 'include',
  method: 'OPTIONS',
};

export { BASE_URL, fetchInit };