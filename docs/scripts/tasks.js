let data_and_info;
async function body() {
	const form = document.querySelector('form')
	const logout = document.getElementById("logout");
	const logout_popup = document.getElementById("logout_popup");
	const confirmLogout = document.getElementById("confirmLogout");
	const cancelLogout = document.getElementById("cancelLogout");

	if (!form) return
	
	form.action = getCookie('url')+'/update';
	const data_and_info_url = form.action.replace('update', 'user-info');
	const logout_url = form.action.replace('update', 'logout');
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
		let info = data_and_info['info'];
		let data = data_and_info['data'];
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

  		const inputs = form.querySelectorAll("input[type='text'], input[type='email']");

		inputs.forEach(input => {
			const key = input.id;
			if (data.hasOwnProperty(key)) input.value = data[key];
		});
	}

	const errorDiv = document.querySelector('#error');

	form.addEventListener('submit', function (e) {
		e.preventDefault();
		errorDiv.textContent = '';
	
		const formData = new FormData(form);
	
		fetch(form.action, {
			headers: {
                "ngrok-skip-browser-warning": "true"
            },
            credentials: "include",
			method: 'POST',
			body: formData
		})

    	.then(response => response.json())

    	.then(data => {
			if (data.success) {
				const url = getCookie('caller') || '/Pokemon';
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
