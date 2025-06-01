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

function callHamster(url='hamster.html') {
    const currentUrl = window.location.href;
    const expires = new Date(Date.now() + 6e5).toUTCString();
    document.cookie = `caller=${encodeURIComponent(currentUrl)}; expires=${expires}; path=/; SameSite=Lax; Secure`;

    window.location.replace('/Pokemon/pages/' + url);
}

async function load_url_into_form() {
	const form = document.querySelector('form');
	if (!form) return;
	
	const url = getCookie('url');
	try {
	    await fetch(url, {
		    headers: {
				"ngrok-skip-browser-warning": "true"
			},
			credentials: "include"
	    });
		form.action = url + '/login'
    } catch {
        callHamster();
    }
}

function hide_and_show(class_of_caller) {
	const extraneous = ("toggle-").length;
	let better_class = '.' + class_of_caller;
	let id_of_caller = '#' + class_of_caller.slice(extraneous);

    const toggleBtn = document.querySelector(better_class);
	const Input  = document.querySelector(id_of_caller);

    const isHidden = Input.type === 'password';
    Input.type = isHidden ? 'text' : 'password';
	const svg_show = better_class + ' .eye-icon'; const svg_hide = better_class + ' .eye-off';

	switch (isHidden) {
		case true:
			document.querySelector(svg_show).style.display = "none";
			document.querySelector(svg_hide).style.display = "block";
			break;
		case false:
			document.querySelector(svg_hide).style.display = "none";
			document.querySelector(svg_show).style.display = "block";
			break;
	}
    toggleBtn.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
}