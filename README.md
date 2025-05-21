# PyPikachu 🎴  
A modular machine learning toolkit for detecting rare visual defects in Pokémon trading cards — starting with the iconic **Wartortle Evolution Box error**.


## 📦 Project Overview

**PokéPrint Inspector** brings together web crawling, computer vision, and neural networks to build a complete pipeline for:

- Acquiring card images from eBay
- Extracting the **evolution portrait region** from cards
- Classifying those portraits as either correct (Squirtle) or defect (Wartortle)


## 🧠 Core Modules

### 🕷️ `spinarak.py` — eBay Image Crawler  
- Authenticates using eBay’s Browse API  
- Searches for listings related to evolution box errors  
- Downloads images to the `images/` directory

### 🎨 `smeargle.py` — Card Image Processor  
- Detects, aligns, and deskews full card images  
- Crops the evolution portrait region from the top-left corner  
- Saves outputs to `adjusted_images/` for easy debugging

### 🧠 `porygon.py` — Portrait Classifier (CNN)  
- Trains a neural network to detect misprints based on cropped ROIs  
- Loads training data from the `dataset/` directory  
- Evaluates predictions and reports results  

🔁 If the full dataset is not present, the program will **automatically download it** from Kaggle:  
🔗 [Kaggle Dataset](https://www.kaggle.com/datasets/benjaminadedowole/wartortle-evolution-error)

### 🧰 `miscellaneous.py` — Shared Utilities  
- Contains reusable helpers for user input, colored printing, and dataset downloading

## 🛠️ Setup Instructions

1. **Clone the Repository**
```bash
git clone https://github.com/HeIsOdin/Pokemon.git
cd Pokemon
````

2. **Create a Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

4. **Set eBay API Credentials**

```bash
export CLIENT_ID=your_ebay_client_id
export CLIENT_SECRET=your_ebay_client_secret
```

5. **Download Dataset Automatically (Optional)**
   If the full dataset is missing, it will be fetched from Kaggle when running `main.py`.

> You’ll need your `kaggle.json` API token from [Kaggle settings](https://www.kaggle.com/settings).
> Place it in the project root or at `~/.kaggle/kaggle.json`.

### 🔐 Kaggle API Authentication

To train the model using the full dataset, `porygon.py` will automatically attempt to download the data from Kaggle.

To do this, you’ll need your **Kaggle API token (`kaggle.json`)**, which can be generated from your [Kaggle account settings](https://www.kaggle.com/settings).

You can provide this token in one of two ways:

#### ✅ Option 1: Save `kaggle.json` in a default location

* **Linux / macOS:**
  Save it to:

  ```
  ~/.kaggle/kaggle.json
  ```

* **Windows:**
  Save it to:

  ```
  C:\Users\<YourUsername>\.kaggle\kaggle.json
  ```

> `porygon.py` will automatically detect and use this file if present.

#### ✅ Option 2: Enter your Kaggle credentials manually

If `kaggle.json` is not found, the program will prompt you to **enter your Kaggle username and API key manually**. This allows `porygon.py` to authenticate and download the dataset without needing the file.

> 🛡️ **Security Note**
> If you're using the official version of this project (from [@HeIsOdin](https://github.com/HeIsOdin)), your credentials will **never be stored, logged, or transmitted elsewhere**.
> That said, if you're running a modified or forked version of this project, **use caution when entering API credentials manually** and **review the code to ensure your data is safe**.



## 🚀 How to Use

Launch the main pipeline from the root of the repo:

```bash
python main.py
```

You’ll be prompted to:

* Crawl for cards (`spinarak`)
* Align & crop ROIs (`smeargle`)
* Train & evaluate the model (`porygon`)

You can also run modules individually:

```bash
python -m spinarak
python -m smeargle
python -m porygon
```



## 🧪 Example Use Cases

* Build a dataset of top-left evolution portraits from real-world cards
* Train a model to detect visual misprints (like Wartortle in Squirtle's place)
* Prototype AI-assisted card grading or defect screening


## 📁 Directory Structure

```
Pokemon/
├── main.py                # Entry point for the entire pipeline
├── spinarak.py            # eBay crawler module
├── smeargle.py            # Image alignment and ROI extraction
├── porygon.py             # CNN training and evaluation
├── miscellaneous.py       # Shared helper functions
├── dataset/               # Contains subdirectories of labeled portrait images
├── images/                # Raw downloaded images from eBay
├── adjusted_images/       # Debug outputs from alignment and cropping
├── requirements.txt
└── README.md
```



## 🙌 Contributors

| Role           | Name                                | GitHub                                         |
| -------------- | ----------------------------------- | ---------------------------------------------- |
| Creator / Lead | Odin                                | [@HeIsOdin](https://github.com/HeIsOdin)       |
| Mentor         | Prof. Andrew Kramer                 | [@Rewzilla](https://github.com/Rewzilla)       |
| Collaborator   | Jessica Senyah                      | [@JessSen22](https://github.com/JessSen22)     |
| Contributor    | Samyam Aryal (image quality advice) | [@samyamaryal](https://github.com/samyamaryal) |


## 📜 License & Dataset Usage

This project and dataset are provided for educational and research purposes. Some images are derived from public listings (e.g., eBay) and may be subject to copyright. Please review usage rights before applying this work commercially.

---
