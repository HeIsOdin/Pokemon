async function fetchDataAndRenderTable(data_and_info_url) {
    try {
        // Fetch JSON from your backend endpoint
        const response = await fetch(data_and_info_url, {
            headers: {
                "ngrok-skip-browser-warning": "true", // useful if using ngrok
                "Content-Type": "application/json"
            },
            credentials: "include" // keeps cookies/session if needed
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data_and_info = await response.json();

        // Grab the "info" part (or use "data" if you prefer)
        let info = data_and_info['info'];
        // let data = data_and_info['data'];  // optional second dataset

        // Render the table
        renderTable(info);

    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

function renderTable(data) {
    const table = document.querySelector("table");
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");

    // Clear previous content
    thead.innerHTML = "";
    tbody.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {
        console.warn("No data available to render.");
        return;
    }

    // Create headers from first object keys
    const keys = Object.keys(data[0]);
    const headerRow = document.createElement("tr");

    keys.forEach(key => {
        const th = document.createElement("th");
        th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);

    // Create rows
    data.forEach(item => {
        const row = document.createElement("tr");

        keys.forEach(key => {
            const td = document.createElement("td");
            td.textContent = item[key] ?? "";
            row.appendChild(td);
        });

        tbody.appendChild(row);
    });
}


