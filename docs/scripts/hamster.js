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
            console.warn('No URL cookie set. Waiting...');
            await delay(10000);
            retries++;
            continue;
        }

        if (state === 'expired') {
            console.log('Refreshing cookies...');
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
                console.log('Server check successful, redirecting...');
                window.location.replace('/Pokemon');
                return;
            } else {
                throw new Error('Server responded with error');
            }
        } catch (error) {
            console.warn('Fetch failed, marking state expired.');
            await setCookie(3, 'expired');
            await delay(10000);
            retries++;
        }
    }

    console.error('Max retries reached. Redirecting to error page.');
    window.location.replace('/Pokemon/pages/server-down.html');
}

waitForCookie();


