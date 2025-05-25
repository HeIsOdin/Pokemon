function handleRetry(retries, timeout) {
    document.documentElement.style.transition = "filter 0.5s ease";
    document.documentElement.style.filter = "grayscale(1)";
    document.body.style.pointerEvents = "none";

    if (retries > 0) {
        console.warn(`🔁 Retrying in ${timeout / 1000} seconds... (${retries} left)`);
        setTimeout(() => {
            get_url_from_JSON(retries - 1, timeout * 2);
        }, timeout);
    } else {
        console.error("❌ All retries exhausted. Giving up.");
    }
}

async function get_url_from_JSON() {
    try {
        const response = await fetch('env.json');
        const data = await response.json();

        const form = document.querySelector('form');
        if (form && data.url && data.state !== "expired") {
            window.location.replace('/Pokemon/pages/main.html');
        }
		return true
    } catch (error) {
        window.location.replace('/Pokemon/pages/unknown.html')
    }
}
