import requests
import os

# ----------------------------------------
# Step 1: Authenticate with eBay API
# ----------------------------------------
def get_ebay_token(client_id: str, client_secret: str) -> str:
    """
    Fetches an OAuth2 access token from the eBay API using client credentials.
    """
    url = 'https://api.ebay.com/identity/v1/oauth2/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'scope': 'https://api.ebay.com/oauth/api_scope'
    }

    # Use HTTP Basic Auth with client ID and secret
    response = requests.post(url, headers=headers, data=data, auth=(client_id, client_secret))
    
    if response.status_code != 200:
        print(f"\033[31m[ERROR] Failed to retrieve token: {response.status_code} - {response.text}\033[0m")
        exit()
    
    return response.json()['access_token']

# ----------------------------------------
# Step 2: Search for Pokémon card listings
# ----------------------------------------
def search_pokemon_cards(access_token: str, query: str ="Evolution Box error Wartortle", limit: int = 30) -> dict:
    """
    Searches eBay listings using the Browse API for the specified Pokémon card query.
    """
    search_url = 'https://api.ebay.com/buy/browse/v1/item_summary/search'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    params = {
        'q': query,
        'limit': str(limit),
        'filter': 'conditionIds:{1000|3000|4000}',  # New, Used, etc
        'category_ids': '183454'  # Collectible Card Games
    }
    response = requests.get(search_url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"\033[31m[ERROR] Search failed: {response.status_code} - {response.text}\033[0m")
        exit()
    return response.json()

# ----------------------------------------
# Step 3: Download card image from eBay
# ----------------------------------------
def download_image(original_image_url: str, title: str, save_dir:str, save: bool= False) -> bytes:
    """
    Downloads the image from the given URL and, in some cases, saves it with a sanitized filename.
    """
    image_url = ""
    try:
        # Try high-res first
        image_url = original_image_url.replace("s-l225.jpg", "s-l1600.jpg")
        response = requests.get(image_url)
        if response.status_code != 200:
            raise Exception("Fallback to low-res!")
    except:
        image_url = original_image_url  # fallback
        print("\033[33m[WARNING] Unable to fetch image with better quality. Falling Back...\033[0m")

    response = requests.get(image_url)

    if save:
        os.makedirs(save_dir, exist_ok=True)

        # Truncate and sanitize title for filename
        filename = f"{title[:40].replace(' ', '_').replace('/', '-')}.jpg" # Ensure this is consistent in smeagle
        filepath = os.path.join(save_dir, filename)

        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"\033[32m[SUCCESS] Saved: {filepath}\033[0m")
        else:
            print(f"\033[31m[ERROR] Failed to download image: {image_url}\033[0m")
    
    return response.content