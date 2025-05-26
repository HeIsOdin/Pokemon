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
        }
    } catch (error) {
        window.location.replace('/Pokemon/pages/hamster.html');
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

async function waitForCookie() {
    if (!getCookie('url') || getCookie('state') === 'expired') {
        await setCookie(3);
        console.clear();
        setTimeout(waitForCookie, 3000);
    } else {
        window.location.replace('/Pokemon/index.html');
    }
}

setCookie(3);
waitForCookie();


