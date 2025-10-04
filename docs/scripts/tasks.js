async function initializeTable() {
    console.log('initializeTable started');
    
    const form = document.querySelector('form');
    console.log('Form found:', !!form);
    
    if (!form) return;
    
    // Simple URL construction for testing
    const baseUrl = window.location.origin;
    const data_and_info_url = baseUrl + '/user-info';
    console.log('Data URL:', data_and_info_url);
    
    try {
        const response = await fetch(data_and_info_url, {
            headers: {
                "heroku-skip-browser-warning": "true"
            },
            credentials: "include"
        });
        console.log('Response status:', response.status);
        
        const data = await response.json();
        console.log('Data received:', data);
        
        // Simple table creation
        const table = document.querySelector('table');
        const tbody = table.querySelector('tbody');
        
        if (data.info && data.info.length > 0) {
            data.info.slice(0, 3).forEach(item => {
                const row = document.createElement('tr');
                Object.values(item).forEach(value => {
                    const td = document.createElement('td');
                    td.textContent = value;
                    row.appendChild(td);
                });
                tbody.appendChild(row);
            });
        }
        
    } catch (error) {
        console.error('Error:', error);
    }
}

document.addEventListener('DOMContentLoaded', initializeTable);
