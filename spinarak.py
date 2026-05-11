"""
# Spinarak
eBay API crawler module for PokéPrint Inspector.

This module handles:
- Authenticating with the eBay API using OAuth2
- Searching Pokémon card listings on eBay with specific queries
- Downloading card images (attempting high-resolution first, falling back if needed)
- Optionally saving images locally or returning them as byte content

Dependencies:
- requests
- os
- sys
- rotom
- dotenv
- logging

This module supports the data acquisition phase of the PokéPrint Inspector
pipeline, enabling automated gathering of card listings and images
for defect detection.
"""

from dotenv import load_dotenv
from time import sleep
from rotom import env
import requests
import os
import sys
import logging

NAME                = 'Spinarak'
DELAY               = 0.25  # seconds between API calls to respect rate limits
TIMEOUT             = 10  # seconds
EBAY_SORTING        = "newlyListed"
EBAY_PAGE_SIZE      = 50
EBAY_ITEM_LIMIT     = 100  # Max total items to fetch across all queries
EBAY_CATEGORY_ID    = '183454'  # eBay category ID for Pokémon Cards
EBAY_CONDITION_IDS  = "1000|3000|4000"
EBAY_BUYING_OPTIONS = "FIXED_PRICE|AUCTION"


def __geteBayToken__(id: str, secret: str, log: logging.Logger) -> str:
    """
    Fetch an OAuth2 access token from the eBay API using client credentials.

    Args:
        - client_id (str): eBay API client ID.
        - client_secret (str): eBay API client secret.

    Returns:
    - str: Access token for authenticated API requests.
    """
    url = 'https://api.ebay.com/identity/v1/oauth2/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'scope': 'https://api.ebay.com/oauth/api_scope'
    }

    response = requests.post(url, headers=headers, data=data, auth=(id, secret), timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    log.debug(f"eBay token response: {data}")
    if not 'access_token' in data: raise Exception(f"Missing access_token: {data}")
    return data['access_token']

def __searchPokemonCards__(token: str, q: str, price: float, log: logging.Logger, offset: int = 0, limit: int = EBAY_ITEM_LIMIT) -> dict:
    """
    Fetches up to `limit` Pokémon card listings from eBay, starting at `offset`, combining paginated results.

    Args:
        - access_token (str) : OAuth2 bearer token.
        - q (str) : Search query string.
        - price (float) : Maximum price filter.
        - offset (int) : Index to start fetching from.
        - limit (int) : Total number of listings to fetch.

    Returns:
        dict: Combined eBay listings in a single JSON-like structure.
    """

    search_url = 'https://api.ebay.com/buy/browse/v1/item_summary/search'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
    }
    filters = {
        'price': f'[0..{price}]',
        'buyingOptions': f'{{{EBAY_BUYING_OPTIONS}}}',
        'conditionIds': f'{{{EBAY_CONDITION_IDS}}}'
    }
    params = {
        'q'            : q,
        'sort'         : EBAY_SORTING,
        'filter'       : f'{','.join([f"{k}:{v}" for k, v in filters.items()])}',
        'category_ids' : EBAY_CATEGORY_ID,
    }

    all_items = []
    total_fetched = 0

    # 1000 = New / Brand New / New Factory Sealed
    # 3000 = Used; for trading cards, this means used
    # 4000 = Very Good; for trading cards, this means ungraded
    while total_fetched < limit:
        batch_limit = min(EBAY_PAGE_SIZE, limit - total_fetched)
        params.update({
            'limit'       : str(batch_limit),
            'offset'      : str(offset + total_fetched),
        })

        response = requests.get(search_url, headers=headers, params=params)

        response.raise_for_status()

        data = response.json()
        items = data.get('itemSummaries', [])
        if not items:
            log.debug(f"No more items found for query '{q}' after fetching {total_fetched} items.")
            break

        all_items.extend(items)
        total_fetched += len(items)

        if len(items) < batch_limit: break

        sleep(DELAY)   

    return {'itemSummaries': all_items}


def __downloadImage__(url: str, log: logging.Logger, title: str,) -> bytes:
    """
    Download an image from eBay and optionally save it locally.

    Args:
        - original_image_url (str): URL of the eBay listing image.
        - title (str): Listing title (used for filename if saving).
        - save_dir (str): Directory path to save the image.
        - save (bool): If True, saves the image to disk; otherwise returns byte content.

    Returns:
    - bytes: Image content as raw bytes.
    """
    resolution_versions = ("1600",)
    # Try fetching high-resolution version first
    for res in resolution_versions:
        high_res_url = url.replace("s-l225.jpg", f"s-l{res}.jpg")
        response = requests.head(high_res_url)
        if response.status_code == 200:
            url = high_res_url
            log.debug(f"Found high-quality image at {url}")
            break
        else:
            log.warning(f"High-quality image not found at {high_res_url} (status code: {response.status_code})")

    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()

    if title:
        os.makedirs('images', exist_ok=True)
        # Sanitize filename
        filepath = f"images/{title[:40].replace(' ', '_').replace('/', '-')}.jpg"
        with open(filepath, 'wb') as f:
            f.write(response.content)
            log.debug(f"Saved image to {filepath}")

    return response.content

def __getCardDetails__(items: dict, log: logging.Logger, debug: bool = False) -> list[dict]:
    """
    Extract relevant card details from an eBay item summary.

    Args:
        - item (dict): eBay item summary JSON object.
    Returns:
        dict: Extracted card details including title, price, condition, and image URL.
    """
    details = []
    for item in items.get('itemSummaries', []):
            title: str = item.get('title', '')
            product_url: str = item.get('itemWebUrl', '')
            image_url: str = item.get('image', {}).get('imageUrl', '')

            if not image_url:
                log.warning(f"No image URL found for {title} - {product_url}")
                continue

            img = bytearray(__downloadImage__(image_url, log, title if debug else ''))
            details.append({'title': title,'url': product_url,'image': img})
    return details

def health(log: logging.Logger) -> tuple[list[str], list[bool]]:
    checklist: list[str] = []
    checks: list[bool] = []

    checklist.append("eBay API Authentication")
    try:
        CLIENT_ID, CLIENT_SECRET = env('EBAY_CLIENT_ID,EBAY_CLIENT_SECRET')
        token = __geteBayToken__(CLIENT_ID, CLIENT_SECRET, logging.getLogger(NAME))
        checks.append(True)
    except Exception as e:
        token = ''
        log.error(f"eBay API authentication failed: {e}")
        checks.append(False)
    
    checklist.append("eBay API Search")
    try:
        results = __searchPokemonCards__(token, price=20.0, q="Wartortle 42/102", log=log, limit=1)
        checks.append('itemSummaries' in results)
    except Exception as e:
        results = {}
        log.error(f"eBay API search failed: {e}")
        checks.append(False)
    
    checklist.append("eBay Listing Image Download")
    try:
        details = __getCardDetails__(results, log)
        if len(details) > 0 and 'image' in details[0]:
            checks.append(True)
        else:
            log.error(f"Image download failed: No valid image found")
            checks.append(False)
    except Exception as e:
        log.error(f"Image download failed: {e}")
        checks.append(False)
    
    return checklist, checks

def main():
    queries = ["Wartortle 42/102", "Wartortle base set"]
    debug = len(sys.argv) > 1 and sys.argv[1] == "debug"
    logger = logging.Logger('Spinarak')
    os.makedirs('logs', exist_ok=True)
    if debug:
        load_dotenv() # docker-compose will set env vars, so no need to load them in production
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
    else:
        logger.setLevel(logging.WARNING)
        LOG_DIR = env('LOG_DIR', 'logs')[0]
        LOG_FILE = f'{LOG_DIR}/{NAME}.log'
        open(LOG_FILE, 'w').close()  # Ensure log file exists
        handler = logging.FileHandler(LOG_FILE)
    formatter = logging.Formatter('[%(name)s] %(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.debug("Starting Spinarak...")
    threshold = 20.0
    CLIENT_ID, CLIENT_SECRET = env('EBAY_CLIENT_ID,EBAY_CLIENT_SECRET')

    logger.debug("Authenticating with eBay...")
    token = __geteBayToken__(CLIENT_ID, CLIENT_SECRET, logger)

    items = []

    for query in queries:
        logger.debug(f"Searching eBay for query: {query} with price threshold: {threshold}")
        results = __searchPokemonCards__(token, price=threshold, q=query, log=logger)

        logger.debug("Downloading listing images...")
        details = __getCardDetails__(results, logger, debug)
        items.extend(details)
            
        logger.debug(f"Total items fetched: {len(items)}")

if __name__ == "__main__":
    main()