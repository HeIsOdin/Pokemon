document.addEventListener("DOMContentLoaded", function () {
    if (getCookie('url') && getCookie('state') === 'active') body();
    else callHamster();
});

let data_and_info;
async function body() {
	const form = document.querySelector('form')
	
	if (!form) return
	
	form.action = getCookie('url')+'/update';
	const data_and_info_url = form.action.replace('update', 'user-info');
    try {
	    const response = await fetch(data_and_info_url, {
		    headers: {
                "ngrok-skip-browser-warning": "true",
                "Content-Type": "application/json"
            },
            credentials: "include"
	    });
        data_and_info = await response.json();
		if ('redirect' in data_and_info) callHamster(data_and_info['redirect']);
    } catch {
		callHamster();
    } finally {
    // Check if data_and_info is valid before using it
    if (data_and_info && data_and_info['info'] && data_and_info['data']) {
        let info = data_and_info['info'];
        let data = data_and_info['data'];
        const table = document.querySelector("table");
        if (!table) return; // Guard for missing table
        const thead = table.querySelector("thead");
        const tbody = table.querySelector("tbody");
        if (!thead || !tbody) return; // Guard for missing thead/tbody

        thead.innerHTML = ""; 
        tbody.innerHTML = "";
        // ... rest of your code ...
    
		if (info.length > 0) {
			const keys = Object.keys(info[0]);
			const headerRow = document.createElement("tr");
    	
			keys.forEach(key => {
				const th = document.createElement("th");
				th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
				headerRow.appendChild(th);
			});
			thead.appendChild(headerRow);
			
			info.forEach(item => {
				const row = document.createElement("tr");
				
				keys.forEach(key => {
					const td = document.createElement("td");
					td.textContent = item[key];
					row.appendChild(td);
				});
				tbody.appendChild(row);
			});
		}
	
