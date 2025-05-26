async function setCookie(hours, state='') {
    try {
        const response = await fetch('/Pokemon/env.json');
        /** @type {{ url: string, state: string }} */
        const data = await response.json();

        if (data) {
            for (const [key, value] of Object.entries(data)) {
                if (key === 'state' && state !== '') value = state;
                const expires = new Date(Date.now() + hours * 36e5).toUTCString();
                document.cookie = `${key}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax; Secure`;
            }
        }
    } catch (error) {
        window.location.replace('/Pokemon/pages/unknown.html');
    }
}

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

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForCookie() {
    while (true) {
        if (getCookie('state') === 'expired') {
            setCookie(3);
            await delay(10000);
        } else {
            try {
                await fetch(url, {
                    headers: { "ngrok-skip-browser-warning": "true" }
                });
                window.location.replace('/Pokemon');
            } catch {
                setCookie(3, 'expired');
                await delay(10000);
                location.reload();
            }
        }
    }
    
}

waitForCookie();

