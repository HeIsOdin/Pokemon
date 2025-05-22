function load_options_from_JSON() {
    fetch('../config.json').then(response => response.json()).then(data => {
        const defect = document.getElementById("defect");
		//const marketplace = document.getElementById("marketplace");
        for (const key in data) {
			const option = document.createElement("option");
			option.value = key;
			option.textContent = data[key]['title'];
			defect.appendChild(option);
		}
	});
};

function body() {
	load_options_from_JSON();
};