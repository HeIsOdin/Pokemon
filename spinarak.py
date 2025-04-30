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
        raise Exception(f"❌ Failed to retrieve token: {response.status_code} - {response.text}")
    
    return response.json()['access_token']

# ----------------------------------------
# Step 2: Search for Pokémon card listings
# ----------------------------------------
def search_pokemon_cards(access_token: str, query="Evolution Box error Wartortle", limit=30) -> dict:
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
        raise Exception(f"❌ Search failed: {response.status_code} - {response.text}")
    
    return response.json()

# ----------------------------------------
# Step 3: Download card image from eBay
# ----------------------------------------
def download_image(image_url: str, title: str, save_dir='images') -> str:
    """
    Downloads the image from the given URL and saves it with a sanitized filename.
    """
    os.makedirs(save_dir, exist_ok=True)

    # Truncate and sanitize title for filename
    filename = f"{title[:40].replace(' ', '_').replace('/', '-')}.jpg"
    filepath = os.path.join(save_dir, filename)

    response = requests.get(image_url)
    
    if response.status_code == 200:
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"[✓] Saved: {filepath}")
    else:
        print(f"[✗] Failed to download image: {image_url}")
    
    return filepath

# ----------------------------------------
# Main Execution
# ----------------------------------------
if __name__ == "__main__":
    # Load credentials from environment variables
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')

    if not CLIENT_ID or not CLIENT_SECRET:
        raise EnvironmentError("❌ CLIENT_ID or CLIENT_SECRET not set in environment.")

    print("[INFO] Authenticating with eBay...")
    token = get_ebay_token(CLIENT_ID, CLIENT_SECRET)

    print("[INFO] Searching for Pokémon card listings...")
    results = search_pokemon_cards(token)

    print("[INFO] Downloading listing images...")
    for item in results.get('itemSummaries', []):
        title = item.get('title', 'no_title')
        image_url = item.get('image', {}).get('imageUrl')
        if image_url:
            download_image(image_url, title)
        else:
            print(f"[!] No image found for: {title}")
