const BASE_URL = 'https://7fe038f5dcfd.ngrok-free.app/pypikachu'
const headerOptions = {
  'ngrok-skip-browser-warning': 'true',
    credentials: 'include'
};

async function logoAnimation() {
    return new Promise((resolve) => {
        const wah = document.querySelector('.wheel-and-hamster');
        const logo = document.getElementById('log');
        const ani = document.getElementById('anim');
        const container = document.querySelector('#container');

        if (!wah || !logo || !ani || !container) {
            console.warn('Required elements not found.');
            resolve();
            return;
        }

        const r = parseFloat(getComputedStyle(wah).height) / 2;
        const offset = Math.sqrt(2 * (r ** 2)) - r;

        document.documentElement.style.setProperty('--spoke_offset', `${offset}px`);
        document.documentElement.style.setProperty('--log_width', `calc(100% - ${2 * r}px - ${offset}px)`);

        logo.style.display = "block";
        container.style.justifyContent = "flex-start";
        logo.style.animation = 'wheelHamster 5s ease-out forwards alternate';
        ani.style.animation = 'textstroke 10s ease-out forwards alternate';

        ani.addEventListener('animationend', () => {
            let opacity = 1;
            const fadeOut = () => {
                if (opacity <= 0) {
                    logo.style.opacity = '0';
                    wah.style.opacity = '0';
                    resolve();  // ✅ resolve when fade-out completes
                    return;
                }
                opacity -= 0.03;
                logo.style.opacity = wah.style.opacity = opacity.toString();
                requestAnimationFrame(fadeOut);
            };
            requestAnimationFrame(fadeOut);
        }, { once: true });
    });
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForActiveUrl() {
    let retries = 0;
    const maxRetries = 40;

    while (retries < maxRetries) {
        const url = BASE_URL;

        if (!url) {
            await delay(5000);
            retries++;
            continue;
        }

        try {
            await fetch(url);
            await logoAnimation();
            window.location.replace('/Pokemon');
            return;
        } catch (error) {
            console.log(error)
            await delay(5000);
            retries++;
        }
    }
    window.location.replace('pages/unknown.html');
}

waitForActiveUrl();


