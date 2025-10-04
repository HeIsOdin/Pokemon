class TableManager {
    constructor(tableSelector = 'table') {
        this.tableSelector = tableSelector;
        this.init();
    }
    
    async init() {
        const dataUrl = this.constructDataUrl();
        await this.fetchAndCreateTable(dataUrl);
    }
    
    constructDataUrl() {
        // Get base URL from cookie or current location
        const baseUrl = this.getCookie('url') || window.location.origin;
        return `${baseUrl}/user-info`;
    }
    
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }
    
    async fetchAndCreateTable(dataUrl) {
        try {
            const response = await fetch(dataUrl, {
                headers: {
                    "heroku-skip-browser-warning": "true",
                    "content-type": "application/json"
                },
                credentials: "include"
            });
            
            const dataAndInfo = await response.json();
            
            if (dataAndInfo.redirect) {
                window.location.href = dataAndInfo.redirect;
                return;
            }
            
            this.createTable(dataAndInfo);
        } catch (error) {
            console.error('Error fetching data for table:', error);
        }
    }
    
    createTable(dataAndInfo) {
        try {
            const info = dataAndInfo.info || [];
            const table = document.querySelector(this.tableSelector);
            
            if (!table) {
                console.error('Table element not found');
                return;
            }
            
            const thead = table.querySelector('thead');
            const tbody = table.querySelector('tbody');
            
            thead.innerHTML = '';
            tbody.innerHTML = '';
            
            if (info.length > 0) {
                const keys = Object.keys(info[0]);
                const headerRow = document.createElement('tr');
                
                keys.forEach(key => {
                    const th = document.createElement('th');
                    th.textContent = key.charAt(0).toUpperCase() + key.slice(1);
                    headerRow.appendChild(th);
                });
                
                thead.appendChild(headerRow);
                
                info.slice(0, 3).forEach(item => {
                    const row = document.createElement('tr');
                    
                    keys.forEach(key => {
                        const td = document.createElement('td');
                        td.textContent = item[key];
                        row.appendChild(td);
                    });
                    
                    tbody.appendChild(row);
                });
            }
        } catch (error) {
            console.error('Error creating table:', error);
        }
    }
}

// Initialize when ready
document.addEventListener('DOMContentLoaded', () => {
    new TableManager();
});


