document.addEventListener("DOMContentLoaded", function () {
    if (getCookie('url') && getCookie('state') === "active") body();
    else window.location.replace('/Pokemon/pages/hamster.html');
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

async function load_options_from_JSON() {
	const form = document.querySelector('form');
	if (!form) return;
	
    form.action = getCookie('url');
	const url = form.action.replace('submit', 'options');
    try {
	    const response = await fetch(url, {
		    headers: { "ngrok-skip-browser-warning": "true" }
	    });

        const data = await response.json();
        defectConfig = data;
    } catch {

        window.location.replace('/Pokemon/pages/hamster.html')
    } finally {
        const defectSelect = document.getElementById("defect");
        defectSelect.innerHTML = '<option value="">-- Choose a defect --</option>';

        for (const key in data) {
		    const option = document.createElement("option");
		    option.value = key;
		    option.textContent = data[key]['title'];
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

async function body() {
		load_options_from_JSON();
}