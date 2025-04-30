# PokéPrint Inspector 🧠🎴

A two-part toolset for detecting known printing defects in Pokémon cards — specifically focusing on the famous **Wartortle Evolution Box error**.

This project includes:

- 🕷️ `spinarak.py`: A web crawler that uses the eBay Browse API to search and download Pokémon card listings.
- 🎨 `smeagle.py`: An image alignment tool that deskews the card and extracts the **evolution portrait region** for analysis or classification.

---

## 🔍 What This Does

### 1. `spinarak.py`
> Crawls eBay for rare or error Pokémon cards and downloads their images locally.

- Authenticates with the eBay API using OAuth2
- Searches for cards using a custom query (e.g., `"Wartortle Evolution Box Error"`)
- Downloads the listing image and saves it as a `.jpg` in the `images/` directory

### 2. `smeagle.py`
> Aligns card images and extracts the **evolution box portrait** region.

- Detects the card in the image via contour/edge detection
- Deskews and crops the card using a perspective transform
- Extracts the region where the evolution portrait is printed (top-left corner)
- Displays the aligned card and cropped region

This is useful for training a model to detect cards that erroneously evolve from Wartortle instead of Squirtle.

---

## 🛠️ Setup

1. **Clone this repo:**

```
git clone https://github.com/yourusername/pokeprint-inspector.git
cd pokeprint-inspector
```

2. **Create a virtual environment**

```
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

3. **Install dependencies**
```
pip install -r requirements.txt
```

4. **Set up your eBay API credentials**
```
export CLIENT_ID=your_ebay_client_id
export CLIENT_SECRET=your_ebay_client_secret
```

## 🚀 Usage

### 🕷️ Crawl for error cards

```
python spinarak.py
python smeagle.py
```

## 🧪 Example Use Case

Use this pipeline to:

- Build a dataset of defect and non-defect cards  
- Train a model to detect visual misprints  
- Automate inspection for collectors or resale authentication  

---

## 🧙 Credits

- Created by [Odin](https://github.com/Odin3141)  
- Inspired by real-world defect detection and card misprints  
- Named after 🕷️ **Spinarak** (the crawler) and 🎨 **Smeargle** (the artist Pokémon)  

