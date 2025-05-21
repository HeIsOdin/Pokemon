import spinarak
import smeargle
import porygon
import miscellaneous

if __name__ == "__main__":
    # -------------------------------
    # Configuration
    # -------------------------------
    input_shape = (128, 128)
    num_classes = 2
    author = 'benjaminadedowole'
    dataset_name = 'wartortle-evolution-error'
    CARD_DIM = (480, 680)
    ROI_BOX = (40, 45, 60, 60)  # (x, y, width, height)

    # -------------------------------
    # Preamble
    # -------------------------------
    _, USE_LOCAL_STORAGE = miscellaneous.make_a_choice('\nUse local storage? Y/n: ', 'n')
    INPUT_DIR = OUTPUT_DIR = ''
    if USE_LOCAL_STORAGE:
        INPUT_DIR, _ = miscellaneous.make_a_choice('Provide the directory path for storing eBay images: ', 'images')
        OUTPUT_DIR, _ = miscellaneous.make_a_choice('Provide the directory path for storing debugging images: ', 'adjusted_images')
    TRAINING_DIR, _ = miscellaneous.make_a_choice('Provide the directory path for storing model dataset: ', 'dataset')
    _, USE_RGB = miscellaneous.make_a_choice('Use RGB? Y/n: ', 'y')
    
    miscellaneous.clear_terminal()

    directoryCheck = miscellaneous.directory_check(TRAINING_DIR)
    attempts = 3
    while not directoryCheck[0]:
        if attempts<0:
            exit()
        TRAINING_DIR = porygon.get_dataset(TRAINING_DIR, author, dataset_name)
        attempts-=1
        directoryCheck = miscellaneous.directory_check(TRAINING_DIR)
    images, labels, filenames = porygon.load_dataset_from_directory(TRAINING_DIR, input_shape)
    porygon.display_sample(images, labels, filenames)
    new_images, new_labels = porygon.convert_and_reshape(images, labels)
    training_images, testing_images, training_labels, testing_labels = porygon.split_dataset(new_images, new_labels)
    AI = porygon.build_model(num_classes, USE_RGB)
    porygon.train_model(AI, training_images, training_labels)
    porygon.evaluate_model(AI, testing_images, testing_labels)
    porygon.predict_and_visualize(AI, testing_images, testing_labels)


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
        print(f"\033[34m[INFO] Processing {item['title']}...\033[0m")
        image = None; path = ''
        if USE_LOCAL_STORAGE:
            image, path = smeargle.load_file_from_directory(item['title'], INPUT_DIR, OUTPUT_DIR)
        else:
            image, path = smeargle.load_file_from_bytearray(item.get('image', None), item.get('title', 'no_title'))
        image_edges = smeargle.detect_edges(image, path)

        approx = smeargle.detect_contours(image_edges)
        if len(approx) != 4:
            print(f"\033[33m[WARNING] Skipping '{item['title']}' — could not detect card corners.\033[0m\n")
            continue

        aligned = smeargle.draw_contours(image, approx, path, CARD_DIM)
        roi = smeargle.roi_extraction(aligned, path, ROI_BOX)
        print(f'\033[32m[SUCCESS] Finished Processing {item['title']}\033[0m\n')

    miscellaneous.pause(10)
