document.addEventListener("DOMContentLoaded", function () {
    body();
  });

let defectConfig = {}; // Store all config data globally

async function get_url_from_JSON(retries, timeout) {
    try {
        const response = await fetch('env.json');
        const data = await response.json();

        const form = document.querySelector('form');
        if (form && data.url && data.state !== "expired") {
            form.action = data.url + '/submit';
        } else {
            handleRetry(retries, timeout);
			return false
        }
		return true
    } catch (error) {
        console.error("❌ Failed to fetch env.json:", error);
        handleRetry(retries, timeout);
		return false
    }
}

function handleRetry(retries, timeout) {
    document.documentElement.style.transition = "filter 0.5s ease";
    document.documentElement.style.filter = "grayscale(1)";
    document.body.style.pointerEvents = "none";

    if (retries > 0) {
        console.warn(`🔁 Retrying in ${timeout / 1000} seconds... (${retries} left)`);
        setTimeout(() => {
            get_url_from_JSON(retries - 1, timeout * 2);
        }, timeout);
    } else {
        console.error("❌ All retries exhausted. Giving up.");
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

async function body(retries=3, timeout=3000) {
	if (await get_url_from_JSON(retries, timeout)) {
		load_options_from_JSON();
	}
};