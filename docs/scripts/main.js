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

function callHamster() {
    const currentUrl = window.location.href;

    // Set the cookie
	const expires = new Date(Date.now() + 6e5).toUTCString();
    document.cookie = `caller=${encodeURIComponent(currentUrl)}; expires=${expires}; path=/; SameSite=Lax; Secure`;

    // Redirect to the internal page
    window.location.replace('/Pokemon/pages/hamster.html');
}

async function load_options_from_JSON() {
	const form = document.querySelector('form');
	if (!form) return;
	
    form.action = getCookie('url')+'/submit';
	const url = form.action.replace('submit', 'options');
    try {
	    const response = await fetch(url, {
		    headers: { "ngrok-skip-browser-warning": "true" }
	    });

        defectConfig = await response.json();
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

async function body() {
    document.cookie = "caller=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
	load_options_from_JSON();
}