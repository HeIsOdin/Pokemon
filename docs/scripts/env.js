const BASE_URL = 'https://d093c952fa38.ngrok-free.app/pypikachu'
const fetchInit = {
  headers: {'ngrok-skip-browser-warning': 'true'},
  credentials: 'include',
  method: 'OPTIONS',
};

export { BASE_URL, fetchInit };