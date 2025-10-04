function generateTable(info, targetElement) {
    // 1. Create the main table structure elements
    let info = data_and_info['info'];
	let data = data_and_info['data'];
    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');

    // Clear any existing content in the target element
    targetElement.innerHTML = '';
    
    // Check if there is any data to process
    if (info && info.length > 0) {
        // 2. Determine column headers from the keys of the first object
        const keys = Object.keys(info[0]);
        const headerRow = document.createElement('tr');

        keys.forEach(key => {
            const th = document.createElement('th');
            // Format header: e.g., 'creation' -> 'Creation'
            // The original code uses: key.charAt(0).toUpperCase() + key.slice(1)
            th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        // 3. Generate the table body rows
        info.forEach(item => {
            const row = document.createElement('tr');
            
            keys.forEach(key => {
                const td = document.createElement('td');
                // The value for the cell is taken from the current item object using the key
                td.textContent = item[key];
                row.appendChild(td);
            });
            
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
    } else {
        // Handle case where info is empty or null
        const message = document.createElement('p');
        message.textContent = 'No data available to generate table.';
        targetElement.appendChild(message);
        return null;
    }

    // 4. Append the complete table to the target element
    targetElement.appendChild(table);
    return table;
}

