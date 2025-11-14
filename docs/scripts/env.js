const BASE_URL = 'https://93d55831773e.ngrok-free.app/pypikachu'
const fetchInit = {
  headers: {'ngrok-skip-browser-warning': 'true'},
  credentials: 'include',
  method: 'OPTIONS',
};

export { BASE_URL, fetchInit };