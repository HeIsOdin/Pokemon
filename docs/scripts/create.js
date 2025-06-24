document.addEventListener("DOMContentLoaded", function () {
    if (getCookie('url') && getCookie('state') === 'active') body();
    else callHamster();
});

let defectConfig = {};

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

async function load_options_from_JSON() {
	const form = document.querySelector('form');
	if (!form) return;
	
    form.action = getCookie('url')+'/submit';
	const url = form.action.replace('submit', 'options');
    try {
	    const response = await fetch(url, {
		    headers: {
                "ngrok-skip-browser-warning": "true",
                "Content-Type": "application/json"
            },
            credentials: "include"
	    });
        defectConfig = await response.json();

        if ('redirect' in defectConfig) callHamster(defectConfig['redirect']); 
    } catch {
		callHamster();
    } finally {
        const defectSelect = document.getElementById("defect");
        defectSelect.innerHTML = '<option value="">-- Choose a defect --</option>';

        for (const key in defectConfig) {
		    const option = document.createElement("option");
		    option.value = key;
		    option.textContent = defectConfig[key]['title'];
		    defectSelect.appendChild(option);
        }

        defectSelect.addEventListener("change", updateMarketplaceOptions);
    }
}

function updateMarketplaceOptions() {
	const selectedDefect = document.getElementById("defect").value;
    const marketplaceSelect = document.getElementById("marketplace");
    marketplaceSelect.innerHTML = '<option value="">-- Choose a marketplace --</option>';

    if (selectedDefect && defectConfig[selectedDefect]) {
		const marketplaces = defectConfig[selectedDefect]["marketplace"] || [];
		marketplaces.forEach(market => {
            const option = document.createElement("option");
            option.value = market;
            option.textContent = market;
            marketplaceSelect.appendChild(option);
        });
    }
}

function submit_form() {
	const form = document.querySelector('form');
	const errorDiv = document.querySelector('#error');

	form.addEventListener('submit', function (e) {
		e.preventDefault();
		errorDiv.textContent = '';
	
		const formData = new FormData(form);
	
		fetch(form.action, {
			method: 'POST',
			body: formData,
			headers: {
                "ngrok-skip-browser-warning": "true",
                "Content-Type": "application/json"
            },
            credentials: "include"
		})

    	.then(response => response.json())

    	.then(data => {
			if (data.success) {
				const url = getCookie('callerII') || '/Pokemon';
				window.location.replace(url)
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

async function body() {
	load_options_from_JSON();
    submit_form();
}