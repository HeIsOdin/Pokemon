document.addEventListener("DOMContentLoaded", function () {
    body();
  });

let defectConfig = {};
let max_retries = 3;
let interval = 15000;

async function get_url_from_JSON() {
    try {
        const response = await fetch('env.json');
        const data = await response.json();

        const form = document.querySelector('form');
        if (form && data.url && data.state !== "expired") {
            form.action = data.url + '/submit';
			if (retries < max_retries) {
				location.reload();
			}
        } else {
            window.location.replace('/Pokemon/pages/hamster.html')
        }
		return true
    } catch (error) {
        window.location.replace('/Pokemon/pages/hamster.html')
    }
}

async function load_options_from_JSON() {
	const form = document.querySelector('form');
	if (!form) return;
	
	const url = form.action.replace('submit', 'options');
	const response = await fetch(url, {
		headers: { "ngrok-skip-browser-warning": "true" }
	});

    const data = await response.json();
    defectConfig = data;

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

async function body(retries=max_retries, timeout=interval) {
	if (await get_url_from_JSON(retries, timeout)) {
		load_options_from_JSON();
	}
};