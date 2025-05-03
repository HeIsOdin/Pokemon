# PokéPrint Inspector 🧠🎴

A three-part toolset for detecting known printing defects in Pokémon cards — with a focus on the iconic **Wartortle Evolution Box error**.

This project includes:

- 🕷️ `spinarak.py`: A web crawler that uses the eBay Browse API to search and download Pokémon card listings.
- 🎨 `smeagle.py`: An image alignment tool that deskews card images and extracts the **evolution portrait region**.
- 🧠 `porygon.py`: A convolutional neural network (CNN) that classifies evolution portraits (e.g., Squirtle vs. Wartortle).

---

## 🔍 What This Does

### 1. `spinarak.py`  
> Crawls eBay for rare or error Pokémon cards and downloads their images locally.

- Authenticates with the eBay API using OAuth2
- Searches listings using a custom query (e.g., `"Wartortle Evolution Box Error"`)
- Downloads listing images to the `images/` directory

---

### 2. `smeagle.py`  
> Aligns card images and extracts the **evolution box portrait** region.

- Detects the card using edge and contour detection
- Applies a perspective transform to deskew the card
- Crops the top-left evolution portrait region
- Saves debug outputs and aligned ROIs to the `adjusted_images/` directory

---

### 3. `porygon.py`  
> Trains a CNN to classify evolution portraits as either correct (Squirtle) or erroneous (Wartortle).

- Loads grayscale portrait ROIs from the `training_images/` directory
- Resizes inputs to 128×128 and normalizes pixel values
- Trains a simple CNN on labeled image data
- Evaluates model performance and outputs predictions

> ⚠️ **Note**: The `training_images/` directory includes only a **partial dataset** due to GitHub file size limits.  
For the complete image set, please visit the original source on Kaggle:  
🔗 [Finger Digits Dataset](https://www.kaggle.com/datasets/roshea6/finger-digits-05)

---

## 🛠️ Setup

1. **Clone the repository**
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

```python spinarak.py```

### Align and extract evolution box ROIs

```python smeagle.py```

### Train the classification model

```python porygon.py```

## 🧪 Example Use Case

Use this pipeline to:

- Build a clean dataset of Pokémon card ROIs
- Train a model to detect visual misprints (like the Wartortle error)
- Automate defect screening for collectors and sellers 

---

## 🧙 Credits

- Created by [Odin](https://github.com/HeIsOdin)  
- Mentored by **Professor Andrew Kramer**, who originally proposed the idea and guided its development  
- Inspired by real-world defect detection and card misprints  
- Named after:
  - 🕷️ **Spinarak** – the web crawler  
  - 🎨 **Smeargle** – the image processor  
  - 🧠 **Porygon** – the machine-learning classifier, made of pixels and code  