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
- miscellaneous.py (for colored console logging)

This module supports the data acquisition phase of the PokéPrint Inspector
pipeline, enabling automated gathering of card listings and images
for defect detection.
"""

import requests
import os
import miscellaneous
import time

def get_ebay_token(client_id: str, client_secret: str) -> str:
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

    response = requests.post(url, headers=headers, data=data, auth=(client_id, client_secret))
    
    if response.status_code != 200:
        miscellaneous.print_with_color(f"Failed to retrieve token: {response.status_code} - {response.text}", 1)
    
    return response.json()['access_token']

def search_pokemon_cards(access_token: str, query: str = "Wartortle Pokemon Card", offset: int = 0, price: float = 50, limit: int = 100) -> dict:
    """
    Fetches up to `limit` Pokémon card listings from eBay, starting at `offset`, combining paginated results.

    Args:
        - access_token (str): OAuth2 bearer token.
        - query (str): Search query string.
        - offset (int): Index to start fetching from.
        - price (float): Maximum price filter.
        - limit (int): Total number of listings to fetch.

    Returns:
    - dict: Combined eBay listings in a single JSON-like structure.
    """

    search_url = 'https://api.ebay.com/buy/browse/v1/item_summary/search'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    all_items = []
    page_size = 50
    total_fetched = 0

    while total_fetched < limit:
        batch_limit = min(page_size, limit - total_fetched)
        params = {
            'q': query,
            'limit': str(batch_limit),
            'offset': str(offset + total_fetched),
            'sort': 'newlyListed',
            'filter': f'conditionIds:{1000|3000|4000},price:[0..{price}]',
            'category_ids': '183454'
        }

        response = requests.get(search_url, headers=headers, params=params)

        if response.status_code != 200:
            miscellaneous.print_with_color(f"Search failed at offset {offset + total_fetched}: {response.status_code} - {response.text}", 1)
            break

        data = response.json()
        items = data.get('itemSummaries', [])
        if not items:
            break

        all_items.extend(items)
        total_fetched += len(items)

        if len(items) < batch_limit:
            break

        time.sleep(0.25)

    return {'itemSummaries': all_items}


def download_image(original_image_url: str, title: str, save_dir: str, save: bool = False) -> bytes:
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
    image_url = ""
    try:
        # Try fetching high-resolution version first
        image_url = original_image_url.replace("s-l225.jpg", "s-l1600.jpg")
        response = requests.get(image_url)
        if response.status_code != 200:
            raise Exception("Fallback to low-res!")
    except:
        image_url = original_image_url  # fallback to original URL
        miscellaneous.print_with_color("Unable to fetch high-quality image. Falling back...", 3)

    response = requests.get(image_url)

    if save:
        os.makedirs(save_dir, exist_ok=True)

        # Sanitize filename
        filename = f"{title[:40].replace(' ', '_').replace('/', '-')}.jpg"
        filepath = os.path.join(save_dir, filename)

        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            miscellaneous.print_with_color(f"Saved: {filepath}", 2)
        else:
            miscellaneous.print_with_color(f"Failed to download image: {image_url}", 1)

    return response.content
