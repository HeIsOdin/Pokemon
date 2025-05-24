document.addEventListener("DOMContentLoaded", function () {
    body();
  });

let defectConfig = {}; // Store all config data globally

async function get_url_from_JSON() {
	return fetch('env.json')
	.then(response => response.json())
	.then(data => {
		const form = document.querySelector('form'); // safer than getElementsByTagName
		if (form && data.url) {
			form.action = data.url + '/submit';
		}
	});
}

async function load_options_from_JSON() {
  const form = document.querySelector('form');
  if (!form) return;

  const url = form.action.replace('submit', 'options');

  try {
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

  } catch (error) {
    console.error("❌ Failed to load options:", error);
	document.documentElement.style.transition = "filter 0.5s ease";
    document.documentElement.style.filter = "grayscale(1)";
    document.body.style.pointerEvents = "none";

    setTimeout(() => {
      load_options_from_JSON();
    }, 3000);
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
	await get_url_from_JSON();
	load_options_from_JSON();
};