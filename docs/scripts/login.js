document.addEventListener("DOMContentLoaded", function () {
		load_url_into_form();
		submit_form();
	//else callHamster();
});

let BASE_URL = 'https://7fe038f5dcfd.ngrok-free.app/pypikachu'

function callHamster(url="hamster.html") {
    window.location.replace('/Pokemon/pages/' + url);
}

async function load_url_into_form() {
	const form = document.querySelector('form');
	if (!form) return;
	
	const url = BASE_URL + '/login';
	try {
	    await fetch(url, {
			credentials: "include"
	    });
		form.action = url
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

function submit_form() {
	const form = document.querySelector('form');
	const errorDiv = document.querySelector('#error');

	form.addEventListener('submit', function (e) {
		e.preventDefault();
		errorDiv.textContent = '';
	
		const formData = new FormData(form);
	
		fetch(form.action, {method: 'POST', body: formData, credentials: "include"})
		.then(response => response.json())
    	.then(data => {
			if (data.success) {
				const url = null || document.querySelector("base").getAttribute("href") || '/';
				window.location.replace(url);
			} else {
				errorDiv.style.display = "block";
				errorDiv.textContent = data.message || 'There was an error.';
			}
		})
		
    	.catch(error => {
			errorDiv.style.display = "block";
			errorDiv.textContent = error.message;
    	});
	});
}