let defectConfig = {};
const BASE_URL = 'https://7fe038f5dcfd.ngrok-free.app/pypikachu'
const headerOptions = {
  'ngrok-skip-browser-warning': 'true',
  credentials: 'include'
};

function callHamster(url="hamster.html") {
    window.location.replace('/Pokemon/pages/' + url);
}

async function load_options_from_JSON() {
	const form = document.querySelector('form');
	if (!form) return;
	
    form.action = BASE_URL+'/submit';
	const url = BASE_URL + '/options';
    try {
	    const response = await fetch(url, {headers: headerOptions});
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
            ...headerOptions,
			method: 'POST',
			body: formData,
		})

    	.then(response => response.json())

    	.then(data => {
			if (data.success) {
				const url = null || '/Pokemon';
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

document.addEventListener('DOMContentLoaded', async () => {
    await body();
});
