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

function load_options_from_JSON() {
    const form = document.querySelector('form');
    if (!form) return;
	url = form.action.replace('submit', 'options')
	console.log(defectConfig)
    fetch(url)
      .then(response => response.json())
      .then(data => {
        defectConfig = data; // Save for later use

        const defectSelect = document.getElementById("defect");
        defectSelect.innerHTML = '<option value="">-- Choose a defect --</option>';

        for (const key in data) {
          const option = document.createElement("option");
          option.value = key;
          option.textContent = data[key]['title'];
          defectSelect.appendChild(option);
        }

        defectSelect.addEventListener("change", updateMarketplaceOptions);
      })
      .catch(error => console.error("Failed to load defect options:", error));
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