# Wartortle Evolution Box Misprint Detection Dataset

This dataset is part of the **PyPikachu** project, which focuses on using computer vision to analyze and validate Pokémon trading cards. This specific subset targets one of the most iconic Pokémon TCG errors — the **Wartortle Evolution Box Misprint** — and provides a labeled dataset of extracted evolution boxes to train and evaluate binary classifiers.

## 📌 About the Misprint

In early Base Set Pokémon cards, a printing error caused some Wartortle cards to display **Wartortle** in the evolution box instead of the correct pre-evolution, **Squirtle**. Since this misprint is a well-known and sought-after collector’s item, detecting it programmatically is both a technical and practical challenge in the realm of trading card authentication.

## 📂 Dataset Structure

Instead of using entire card images, this dataset contains **cropped evolution box regions** extracted using OpenCV. This approach focuses model training on the part of the card where the misprint occurs, improving accuracy and reducing noise.

There are two classes:
- `squirtle`: Evolution boxes showing the correct pre-evolution (Squirtle)
- `wartortle`: Misprinted evolution boxes showing Wartortle

### Files and Folders:
```
images/
├── Squirtle
    ├──squirtle0__0.jpg
    ├──squirtle1__0.jpg
    └── ...
├── Wartortle
    ├──squirtle0__0.jpg
    ├──squirtle1__0.jpg
    └── ...
README.md
```

## 🧠 Use Cases

This dataset is ideal for:
- Binary image classification of small, domain-specific visual elements
- Building lightweight image models for TCG card validation
- Exploring region-of-interest (ROI) based training instead of full-image classification
- Demonstrating real-world use of deep learning for anomaly detection in collectibles

## 🔧 Technical Details

- Image formats: `.jpg` and `.png`
- Region of interest: Evolution box area extracted from Wartortle card scans
- Preprocessing: OpenCV used for cropping and transforming card images
- Resolution: Variable (resizing recommended before training)
- Balanced class distribution
- Manually verified and labeled samples

## 🧪 Model Example

A sample deep learning model that classifies these cropped evolution boxes using PyTorch/TensorFlow is available in the [PyPikachu GitHub Repository](https://github.com/heisodin/Pokemon). The model can be trained to detect whether a Wartortle card is a legitimate print or a known misprint based solely on its evolution box.

## 🧑‍🤝‍🧑 Collaborators

- **Andrew Kramer** – Mentor, professor, and originator of the project idea  
  GitHub: [@Rewzilla](https://github.com/Rewzilla)

- **Jessica Senyah** – Close friend and prominent collaborator  
  GitHub: [@JessSen22](https://github.com/JessSen22)

- **Samyam Aryal** – Contributed key improvements to image quality processing via advanced reshaping and region-of-interest selection  
  GitHub: [@samyamaryal](https://github.com/samyamaryal)

## ⚖️ License

This dataset is released under the **Creative Commons Attribution 4.0 International (CC BY 4.0)** license. Please provide credit when using it in your projects, academic papers, or public applications.

## 🙌 Acknowledgements

Special thanks to the Pokémon card collecting community for inspiring this work, and to everyone who contributed to the PyPikachu project. The evolution box extraction process was made possible by community feedback and experimentation.

## 🔗 Related Links

- 🔍 [More on the Wartortle Misprint (Bulbapedia)](https://bulbapedia.bulbagarden.net/wiki/Wartortle_(Base_Set_42))  
- 📊 [PyPikachu Project on GitHub](https://github.com/heisodin/Pokemon)

*Created by Benjamin Adedowole*  
*Maintained as part of the PyPikachu project*
