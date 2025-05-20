import spinarak
import smeargle
import porygon
import miscellaneous

USE_LOCAL_STORAGE = False
INPUT_DIR = OUTPUT_DIR = TRAINING_DIR = ''

if __name__ == "__main__":
    USE_LOCAL_STORAGE = miscellaneous.make_a_choice('\nUse local storage? Y/n: ', 'n')[1]
    if USE_LOCAL_STORAGE:
        INPUT_DIR, _ = miscellaneous.make_a_choice('Provide the directory path for storing downloaded images: ', 'images')
        OUTPUT_DIR, _ = miscellaneous.make_a_choice('Provide the directory path for storing debugging images: ', 'adjusted_images')
        TRAINING_DIR, _ = miscellaneous.make_a_choice('Provide the directory path for storing image dataset: ', 'training_data')
    
    miscellaneous.clear_terminal()

    CLIENT_ID, CLIENT_SECRET = miscellaneous.credentials()

    print("\033[34m[INFO] Authenticating with eBay...\033[0m")
    token = spinarak.get_ebay_token(CLIENT_ID, CLIENT_SECRET)

    print("\033[34m[INFO] Searching for Pokémon card listings...\033[0m")
    results = spinarak.search_pokemon_cards(token)

    print("\033[34m[INFO] Downloading listing images...\033[0m")
    items = []
    for item in results.get('itemSummaries', []):
        card = {}
        card['title'] = item.get('title', 'no_title')
        image_url = item.get('image', {}).get('imageUrl')
        if image_url:
            card['image'] = bytearray(spinarak.download_image(image_url, card['title'], INPUT_DIR, USE_LOCAL_STORAGE))
        else:
            print(f"\033[31m[ERROR] No image found for: {card['title']}\033[0m")
        items.append(card)
    print('\033[32m[SUCCESS] Listed Images have been downloaded! 🥳')

    miscellaneous.pause(10)

    for item in items:
        print(f"\n\033[34m[INFO] Processing {item['title']}...\033[0m")
        image = None; path = ''
        if USE_LOCAL_STORAGE:
            image, path = smeargle.load_file_from_directory(item['title'], INPUT_DIR, OUTPUT_DIR)
        else:
            image, path = smeargle.load_file_from_bytearray(item.get('image', None), item.get('title', 'no_title'))
        image_edges = smeargle.detect_edges(image, path)

        approx = smeargle.detect_contours(image_edges)
        if len(approx) != 4:
            print(f"\033[33m[WARNING] Skipping '{item['title']}' — could not detect card corners.\033[0m")
            continue

        aligned = smeargle.draw_contours(image, approx, path)
        roi = smeargle.roi_extraction(aligned, path)
        print(f'\033[32m[SUCCESS] Finished Processing {item['title']}\033[0m')

    miscellaneous.pause(10)

    images, labels, filenames = porygon.load_dataset_from_directory(TRAINING_DIR)
    porygon.display_sample(images, labels, filenames)
    new_images, new_labels = porygon.convert_and_reshape(images, labels)
    training_images, testing_images, training_labels, testing_labels = porygon.split_dataset(new_images, new_labels)
    AI = porygon.build_model()
    porygon.train_model(AI, training_images, training_labels)
    porygon.evaluate_model(AI, testing_images, testing_labels)
    porygon.predict_and_visualize(AI, testing_images, testing_labels)

