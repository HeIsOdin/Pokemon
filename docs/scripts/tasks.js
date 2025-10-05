document.addEventListener("DOMContentLoaded", function () {
    if (getCookie('url') && getCookie('state') === 'active') body();
    else callHamster();
});

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

let info;
async function body() {
    let url = getCookie('url') + '/user-info';
    try {
	    const response = await fetch(url, {
		    headers: {
                "ngrok-skip-browser-warning": "true",
                "Content-Type": "application/json"
            },
            credentials: "include"
	    });
        info = await response.json()['info'];
		if ('redirect' in data_and_info) callHamster(data_and_info['redirect']);
    } catch {
		callHamster();
    } finally {
		const table = document.querySelector("table");
  		const thead = table.querySelector("thead");
  		const tbody = table.querySelector("tbody");
		
		thead.innerHTML = ""; tbody.innerHTML = "";
		
		if (info.length > 0) {
			const keys = Object.keys(info[0]);
			const headerRow = document.createElement("tr");
    	
			keys.forEach(key => {
				const th = document.createElement("th");
				th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
				headerRow.appendChild(th);
			});
			thead.appendChild(headerRow);
			
			info.slice(0,3).forEach(item => {
				const row = document.createElement("tr");
				
				keys.forEach(key => {
					const td = document.createElement("td");
					td.textContent = item[key];
					row.appendChild(td);
				});
				tbody.appendChild(row);
			});
		}
    }
}
