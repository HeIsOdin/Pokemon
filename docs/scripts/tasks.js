document.addEventListener("DOMContentLoaded", () => {
  if (getCookie('url') && getCookie('state') === 'active') init();
  else callHamster();
});

function getCookie(name) {
  const cookies = document.cookie.split('; ');
  for (let cookie of cookies) {
    const [k, v] = cookie.split('=');
    if (k === name && v !== "") return decodeURIComponent(v);
  }
  return null;
}

let data_and_info;

async function init() {
  const base = getCookie('url');
  const infoUrl = base + '/user-info';

  try {
    const res = await fetch(infoUrl, {
      headers: {
        "ngrok-skip-browser-warning": "true",
        "Content-Type": "application/json"
      },
      credentials: "include"
    });
    data_and_info = await res.json();
    if ('redirect' in data_and_info) return callHamster(data_and_info['redirect']);
  } catch {
    return callHamster();
  }

  // Build table
  const info = data_and_info?.info || [];
  const table = document.getElementById("tasks-table");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");
  thead.innerHTML = ""; tbody.innerHTML = "";

  if (info.length) {
    const keys = Object.keys(info[0]);
    const headerRow = document.createElement("tr");
    keys.forEach(k => {
      const th = document.createElement("th");
      th.textContent = k.charAt(0).toUpperCase() + k.slice(1);
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    info.forEach(item => {
      const tr = document.createElement("tr");
      // Store the raw object on the row for the drawer
      tr.dataset.row = JSON.stringify(item);

      keys.forEach(k => {
        const td = document.createElement("td");
        td.textContent = item[k];
		td.title = String(item[key] ?? "");
        tr.appendChild(td);
      });

      tr.addEventListener("click", onRowClick);
      tbody.appendChild(tr);
    });
  }

  // Remove preload after first frame (matches homepage behavior)
  requestAnimationFrame(() => document.body.classList.remove('is-preload'));
}

/* --- Drawer logic --- */
const drawer = document.getElementById('task-drawer');
const metaList = document.getElementById('drawer-meta');
const statusEl = document.getElementById('drawer-status');
const lastRunEl = document.getElementById('drawer-last-run');
const notesEl = document.getElementById('drawer-notes');

function onRowClick(e) {
  const tr = e.currentTarget;
  const item = JSON.parse(tr.dataset.row);

  // Fill placeholder fields — adjust keys as your API grows
  metaList.innerHTML = "";
  Object.entries(item).forEach(([k, v]) => {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${escapeHtml(titleCase(k))}:</strong> ${escapeHtml(String(v))}`;
    metaList.appendChild(li);
  });

  statusEl.textContent = item.status || 'Unknown';
  lastRunEl.textContent = item.last_run || '—';
  // notesEl.textContent stays as placeholder for now

  openDrawer();
}

function openDrawer() {
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  document.addEventListener('keydown', onEsc, { once: true });
}
function closeDrawer() {
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
}
drawer.addEventListener('click', (e) => {
  if (e.target.hasAttribute('data-close')) closeDrawer();
});

function onEsc(e) {
  if (e.key === 'Escape') closeDrawer();
}

/* --- Helpers --- */
function titleCase(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

function callHamster(url='hamster.html') {
  const currentUrl = window.location.href;
  const expires = new Date(Date.now() + 6e5).toUTCString();
  document.cookie = `caller=${encodeURIComponent(currentUrl)}; expires=${expires}; path=/; SameSite=Lax; Secure`;
  window.location.replace('/Pokemon/pages/' + url);
}
