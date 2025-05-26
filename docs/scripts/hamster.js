async function setCookie(hours, state='') {
    try {
        const response = await fetch('/Pokemon/env.json');
        /** @type {{ url: string, state: string }} */
        const data = await response.json();

        if (data) {
            for (const [key, originalValue] of Object.entries(data)) {
                const value = (key === 'state' && state !== '') ? state : originalValue;
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
    let retries = 0;
    const maxRetries = 10;

    while (retries < maxRetries) {
        const state = getCookie('state');
        const url = getCookie('url');

        if (!url) {
            await delay(10000);
            retries++;
            continue;
        }

        if (state === 'expired') {
            await setCookie(3);
            await delay(10000);
            retries++;
            continue;
        }

        try {
            const response = await fetch(url, {
                headers: { "ngrok-skip-browser-warning": "true" }
            });

            if (response.ok) {
                window.location.replace('/Pokemon');
                return;
            }
        } catch (error) {
            await setCookie(3, 'expired');
            await delay(10000);
            retries++;
        }
    }
    window.location.replace('/Pokemon/pages/server-down.html');
}

waitForCookie();


