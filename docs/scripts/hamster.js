async function logo_animation() {
    // Get elements
    const wah = document.querySelector('.wheel-and-hamster');
    const logo = document.getElementById('log');
    const ani = document.getElementById('anim');
    
    // Calculate dimensions
    const r = parseFloat(getComputedStyle(wah).height) / 2;
    const offset = Math.sqrt(2 * (r ** 2)) - r;
    
    // Set CSS variables
    document.documentElement.style.setProperty('--spoke_offset', `${offset}px`);
    document.documentElement.style.setProperty('--log_width', `calc(100% - ${2 * r}px - ${offset}px)`);
    
    // Apply initial animations
    logo.style.display = "block"; document.getElementById('container').style.justifyContent('flex-start');
    logo.style.animation = 'wheelHamster 5s ease-out forwards alternate';
    ani.style.animation = 'textstroke 10s ease-out forwards alternate';

    // Handle animation end
    ani.addEventListener('animationend', () => {
        let opacity = 1;
        const fadeOut = () => {
            if (opacity <= 0) {
                logo.style.opacity = '0';
                wah.style.opacity = '0';
                return;
            }
            opacity -= 0.03;
            logo.style.opacity = wah.style.opacity = opacity.toString();
            requestAnimationFrame(fadeOut);
        };
        requestAnimationFrame(fadeOut);
    });
}

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
            await setCookie(3);
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
            await fetch(url, {
                headers: { "ngrok-skip-browser-warning": "true" }
            });
            console.log('passed');
            await logo_animation();
            window.location.replace('/Pokemon');
            return;
        } catch (error) {
            console.log(error)
            await setCookie(3, 'expired');
            await delay(10000);
            retries++;
        }
    }
    window.location.replace('/Pokemon/pages/server-down.html');
}

waitForCookie();


