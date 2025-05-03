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

### 3. `model.py`
> Trains a CNN to distinguish between evolution portraits (e.g., Squirtle vs. Wartortle) based on the cropped ROI images.

- Loads grayscale ROI images from the `training_images/` directory
- Resizes inputs to 128×128 and normalizes pixel values
- Trains a simple Convolutional Neural Network (CNN) on labeled image data
- Outputs predictions and evaluation metrics

This model is intended to help automatically detect whether a card has a correct or erroneous evolution box.

> ⚠️ **Note**: The `training_images/` directory contains only a partial dataset due to GitHub file size constraints.  
To access the full dataset, please visit the original source:  
🔗 [Finger Digits Dataset on Kaggle](https://www.kaggle.com/datasets/roshea6/finger-digits-05)

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

- Created by [Odin](https://github.com/HeIsOdin)  
- Mentored by **Professor Andrew Kramer**, who originally proposed the idea and guided its development  
- Inspired by real-world defect detection and card misprints  
- Named after 🕷️ **Spinarak** (the crawler) and 🎨 **Smeargle** (the artist Pokémon)  
 

