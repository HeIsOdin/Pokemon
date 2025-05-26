async function setCookie(hours) {
    try {
        const response = await fetch('/Pokemon/env.json');
        /** @type {{ url: string, state: string }} */
        const data = await response.json();

        if (data) {
            for (const [key, value] of Object.entries(data)) {
                const expires = new Date(Date.now() + hours * 36e5).toUTCString();
                console.log(`${key}, ${value}, ${expires}`);
                document.cookie = `${key}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax; Secure`;
            }
            return data.url;
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
  while (getCookie('state') === 'expired') {
    setCookie('state', 'active', 3);
    await delay(3000);
  }

  window.location.replace('/Pokemon/index.html');
}

waitForCookie();

