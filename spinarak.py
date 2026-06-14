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
- msgpack
- hashlib
- logging

This module supports the data acquisition phase of the PokéPrint Inspector
pipeline, enabling automated gathering of card listings and images
for defect detection.
"""

from time import sleep
from requests.exceptions import HTTPError, ConnectionError, Timeout
from rotom import (
    configure_logger,
    env,
    module_arguments,
    sanitize_filename,
    save_image,
    load_config
)

import requests
import os
import sys
import shutil
import logging
import msgpack
import hashlib

_NAME               = 'spinarak'
DELAY               = 0.25  # seconds between API calls to respect rate limits
TIMEOUT             = 10    # seconds
DOWNLOAD_DIR        = env("INPUT_DIR", os.path.join('.', 'input'))[0]
EBAY_SORTING        = "newlyListed"
EBAY_PAGE_SIZE      = 50
EBAY_ITEM_LIMIT     = 100  # Max total items to fetch across all queries
EBAY_CATEGORY_ID    = '183454'  # eBay category ID for Pokémon Cards
EBAY_CONDITION_IDS  = "1000|3000|4000"
EBAY_BUYING_OPTIONS = "FIXED_PRICE|AUCTION"

def _get_ebay_token(id: str, secret: str) -> str:
    """
    Fetch an OAuth2 access token from the eBay API using client credentials.

    Args:
        - client_id (str)     : eBay API client ID.
        - client_secret (str) : eBay API client secret.

    Returns:
        str: Access token for authenticated API requests.
    """
    logger = logging.getLogger(_NAME)
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
    logger.debug(f"eBay token response: {data}")
    if not 'access_token' in data: raise Exception(f"Missing access_token: {data}")
    return data['access_token']

def _search_pokemon_cards(token: str, query: str, price: tuple[float, float], limit: int) -> dict:
    """
    Fetches up to `limit` Pokémon card listings from eBay, combining paginated results.

    Args:
        - token (str)   : OAuth2 bearer token.
        - query (str)   : Search query string.
        - price (tuple) : Price range as (min_price, max_price).
        - limit (int)   : Total number of listings to fetch.
        - offset (int)  : Index to start fetching from.

    Returns:
        dict: Combined eBay listings in a single JSON-like structure.
    """
    EBAY_SORTING        = "newlyListed"
    EBAY_PAGE_SIZE      = 50
    #EBAY_ITEM_LIMIT     = 100  # Max total items to fetch across all queries
    EBAY_CATEGORY_ID    = '183454'  # eBay category ID for Pokémon Cards
    EBAY_CONDITION_IDS  = "1000|3000|4000"
    EBAY_BUYING_OPTIONS = "FIXED_PRICE|AUCTION"
    logger = logging.getLogger(_NAME)
    search_url = 'https://api.ebay.com/buy/browse/v1/item_summary/search'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'
    }
    filters = {
        'price': f'[{price[0]}..{price[1]}]',
        'buyingOptions': f'{{{EBAY_BUYING_OPTIONS}}}',
        'conditionIds': f'{{{EBAY_CONDITION_IDS}}}',
        'priceCurrency': 'USD',
    }
    if price == float('inf'): del filters['price']  # Remove price filter if no max price is set
    all_items = []
    total_fetched = 0

    # 1000 = New / Brand New / New Factory Sealed
    # 3000 = Used; for trading cards, this means used
    # 4000 = Very Good; for trading cards, this means ungraded
    while total_fetched < limit:
        batch_limit = min(EBAY_PAGE_SIZE, limit - total_fetched)
        params = {
            'q'            : query,
            'sort'         : EBAY_SORTING,
            'filter'       : f'{','.join([f"{k}:{v}" for k, v in filters.items()])}',
            'category_ids' : EBAY_CATEGORY_ID,
            'limit'        : str(batch_limit),
            'offset'       : str(total_fetched),
        }

        response = requests.get(search_url, headers=headers, params=params, timeout=TIMEOUT)

        response.raise_for_status()

        data: dict = response.json()
        items = data.get('itemSummaries', [])
        if not items:
            logger.debug(f"No more items found for '{query}' after fetching {total_fetched} items.")
            break

        all_items.extend(items)
        total_fetched += len(items)

        if len(items) < batch_limit: break

        sleep(DELAY)   

    return {'itemSummaries': all_items}

def _download_image(url: str) -> bytes:
    """
    Download an image from eBay and optionally save it locally.

    Args:
        - url (str)   : URL of the eBay listing image.
        - title (str) : Listing title (used for filename if saving).

    Returns:
        bytes: Image content as raw bytes.
    """
    logger = logging.getLogger(_NAME)
    resolution_versions = ("1600", "800")
    for res in resolution_versions:
        high_res_url = url.replace("s-l225.jpg", f"s-l{res}.jpg")
        response = requests.get(high_res_url, timeout=TIMEOUT)
        if response.status_code != 200:
            logger.debug(f"Failed to fetch at {res} resolution. Code: {response.status_code}")
            continue

        return response.content
    raise Exception(f"Failed to download image from {url}")

def _get_card_details(items: dict, img_hashes: set, debug: bool = False) -> list[dict]:
    """
    Extract relevant card details from an eBay item summary.

    Args:
        - item (dict)      : eBay item summary JSON object.
        - img_hashes (set) : Set of existing image hashes to avoid duplicates.
        - debug (bool)     : If True, saves images locally for debugging purposes.
    Returns:
        list[dict]: List of dictionaries containing card details and image bytes.
        The card details include:
        - title (str) : The title of the eBay listing.
        - url (str)   : The URL of the eBay listing.
        - image (bytes): The raw bytes of the card image.
        - itemId (str): The unique eBay item ID for the listing.
    """
    logger = logging.getLogger(_NAME)
    details = []
    for item in items.get('itemSummaries', []):
            
            title     = str(item.get('title', ''))
            item_id   = str(item.get('itemId', ''))
            prod_url  = str(item.get('itemWebUrl', ''))
            image_url = str(item.get('image', {}).get('imageUrl', ''))

            if not item_id:
                logger.warning(f"No item ID found for listing: {title} - {prod_url}")
                continue

            if not image_url:
                logger.warning(f"No image URL found for {title} - {prod_url}")
                continue

            title = f"{sanitize_filename(title)}"
            img = bytearray(_download_image(image_url))

            pypikachuId = hashlib.md5(img).hexdigest()
            img_hash = f"{pypikachuId[:8]}.jpg"
            if img_hash in img_hashes:
                logger.warning(f"Skipping duplicate image for {title}")
                continue

            if debug:
                path = os.path.join(DOWNLOAD_DIR, img_hash)
                logger.debug(f"Saving image for '{title}' with hash {img_hash} at {path}")
                save_image(img, path)

            details.append({
                'id': pypikachuId,
                'title': title,
                'url': prod_url,
                'image_url': image_url,
                'image': img,
                'itemId': item_id})
            img_hashes.add(img_hash)
    return details

def health(**kwargs) -> tuple[list[str], list[bool]]:
    """
    Perform health checks to verify eBay API connectivity and functionality. 
    """
    debug = True

    configure_logger(_NAME, debug=debug)
    log = logging.getLogger(_NAME)
    checklist: list[str] = []
    checks: list[bool] = []
    img_hashes = set()

    query: str = kwargs.get('queries', ["Wartortle 42/102"])[0]
    threshold: tuple[float, float] = kwargs.get('min_price', 1), kwargs.get('max_price', float('inf'))

    checklist.append("Image hashes bucket is accessible")
    try:
        if not os.path.exists(f"{_NAME}.bin"):
            with open(f"{_NAME}.bin", 'wb') as f: pass
        with open(f"{_NAME}.bin", 'rb') as f:
            unpacked = msgpack.unpack(f)
            img_hashes = set(unpacked) if isinstance(unpacked, list) else set()
        checks.append(True)
    except Exception as e:
        log.exception(f"Failed to access image hashes bucket: {e}")
        checks.append(False)

    checklist.append("eBay API Authentication")
    try:
        token = _get_ebay_token(env('EBAY_CLIENT_ID')[0], env('EBAY_CLIENT_SECRET')[0])
        checks.append(True)
    except Exception as e:
        token = ''
        log.exception(f"eBay API authentication failed: {e}")
        checks.append(False)
    
    checklist.append("eBay API Search")
    try:
        results = _search_pokemon_cards(token, query, threshold, 1)
        checks.append('itemSummaries' in results)
    except Exception as e:
        results = {}
        log.exception(f"eBay API search failed: {e}")
        checks.append(False)
    
    checklist.append("eBay Listing Image Download")
    try:
        details = _get_card_details(results, img_hashes, debug=True)
        if len(details) > 0 and 'image' in details[0]:
            checks.append(True)
        else:
            log.error(f"Image download failed: No valid image found")
            checks.append(False)
    except Exception as e:
        log.exception(f"Image download failed: {e}")
        checks.append(False)
    return checklist, checks

def run(**kwargs) -> list[dict]:
    debug: bool = kwargs.get('debug', False)
    config: dict = load_config(_NAME, kwargs.get('config', {}))

    queries: list[str] = config.get('queries', [])
    thresholds: tuple[float, float] = config.get('min_price', 1), config.get('max_price', float('inf'))
    limit: int = config.get('limit', EBAY_ITEM_LIMIT)

    configure_logger(_NAME, debug=debug)
    logger = logging.getLogger(_NAME)

    if not os.path.exists(f"{_NAME}.bin") or os.path.getsize(f"{_NAME}.bin") == 0:
        with open(f"{_NAME}.bin", 'wb') as f:
            msgpack.pack([], f)
    with open(f"{_NAME}.bin", 'rb') as f:  # Ensure we have a set of item IDs to avoid duplicates
        unpacked = msgpack.unpack(f)
        img_hashes = set(unpacked) if isinstance(unpacked, list) else set()
    logger.debug(f"Loaded {len(img_hashes)} existing image hashes.")

    logger.debug(f"Starting {_NAME}...")
    if debug and os.path.isdir(DOWNLOAD_DIR): shutil.rmtree(DOWNLOAD_DIR)
    logger.debug(f"Loading eBay API credentials...")
    CLIENT_ID, CLIENT_SECRET = env('EBAY_CLIENT_ID,EBAY_CLIENT_SECRET')
    logger.debug("Authenticating with eBay...")
    token = _get_ebay_token(CLIENT_ID, CLIENT_SECRET)

    items: list[dict] = []
    for query in queries:
        logger.debug(f"Searching for {query} with price between {thresholds[0]} and {thresholds[1]}...")
        results = _search_pokemon_cards(token, query, thresholds, limit)

        logger.debug("Downloading listing images...")
        details = _get_card_details(results, img_hashes, debug)
        items.extend(details)
            
        logger.debug(f"Total items fetched: {len(items)}")
    
    with open(f"{_NAME}.bin", 'wb') as f: msgpack.pack(list(img_hashes), f)
    logger.debug(f"Stored {len(img_hashes)} image hashes to {_NAME}.bin")
    return items

def main():
    args = module_arguments(
        desc="Spinarak: eBay API crawler for Pokémon card listings and images.",
        subcommands={
            'run': {
                'desc': "Run the Spinarak crawler with optional parameters.",
                'args': {
                    '--queries': {
                        'type': str,
                        'nargs': '+',
                        'default': ["Wartortle 42/102"],
                        'help': "List of search queries to fetch listings for."
                    },
                    '--threshold': {
                        'type': float,
                        'default': float('inf'),
                        'help': "Maximum price threshold for listings."
                    },
                    '--limit': {
                        'type': int,
                        'default': EBAY_ITEM_LIMIT,
                        'help': "Maximum number of items to fetch per query."
                    },
                    '--debug': {
                        'action': 'store_true',
                        'help': "Enable debug mode with verbose logging and local image saving."
                    },
                }
            },
            "health": {
                'desc': "Run health checks to verify eBay API connectivity and functionality.",
            }
        }
    )
    if not hasattr(args, 'command'):
        print("No command provided. Use --help for usage information.")
        sys.exit(1)
    if args.command == 'health':
        checklist, checks = health()
        for item, check in zip(checklist, checks): print(f"{item}: {"PASS" if check else "FAIL"}")
    elif args.command == "run": run(**{k: v for k, v in vars(args).items() if k != 'command'})
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

if __name__ == "__main__":
    main()