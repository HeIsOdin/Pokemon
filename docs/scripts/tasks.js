// Example: data_and_info is passed from your Python backend
// It should look like:
// data_and_info = {
//     "info": [
//         { "id": 1, "name": "Alice", "age": 23 },
//         { "id": 2, "name": "Bob", "age": 30 }
//     ],
//     "data": [
//         { "score": 85, "grade": "B" },
//         { "score": 92, "grade": "A" }
//     ]
// };

let info = data_and_info['info'];
let data = data_and_info['data'];

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

    // Get headers from first object keys
    const keys = Object.keys(data[0]);
    const headerRow = document.createElement("tr");

    keys.forEach(key => {
        const th = document.createElement("th");
        th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);

    // Add all rows
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

// Call this to render your "info" dataset
renderTable(info);

// If you want to render "data" instead, call:
// renderTable(data);

