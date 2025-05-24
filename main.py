import spinarak
import smeargle
import porygon
import miscellaneous

def main(defect: str, USE_LOCAL_STORAGE: bool, USE_RGB: bool, download_dataset: bool):
    author, dataset_name, input_shape, num_classes, CARD_DIM, ROI_BOX, INPUT_DIR, OUTPUT_DIR, TRAINING_DIR  = miscellaneous.parse_JSON_as_arguments('config.json', defect, ["input_shape", "dataset", "num_classes","dimensions","roi","local_storage","input_dir","debugging_dir","rgb", "training_dir"])
    
    miscellaneous.clear_terminal()

    directoryCheck = miscellaneous.directory_check(TRAINING_DIR)
    attempts = 3
    while not directoryCheck:
        if attempts < 0:
            exit()
        TRAINING_DIR = porygon.get_dataset(TRAINING_DIR, author, dataset_name, download_dataset, USE_LOCAL_STORAGE)
        attempts -= 1
        directoryCheck = miscellaneous.directory_check(TRAINING_DIR)

    images, labels, filenames = porygon.load_dataset_from_directory(TRAINING_DIR, input_shape, USE_RGB)
    porygon.display_sample(images, labels, filenames)
    new_images, new_labels = porygon.convert_and_reshape(images, labels)
    training_images, testing_images, training_labels, testing_labels = porygon.split_dataset(new_images, new_labels)
    AI = porygon.build_model(num_classes, USE_RGB)
    porygon.train_model(AI, training_images, training_labels)
    porygon.evaluate_model(AI, testing_images, testing_labels)
    porygon.predict_and_visualize(AI, testing_images, testing_labels, USE_RGB)

    CLIENT_ID, CLIENT_SECRET = miscellaneous.credentials()

    miscellaneous.print_with_color("Authenticating with eBay...", 4)
    token = spinarak.get_ebay_token(CLIENT_ID, CLIENT_SECRET)

    miscellaneous.print_with_color("Searching for Pokémon card listings...", 4)
    results = spinarak.search_pokemon_cards(token)

    miscellaneous.print_with_color("Downloading listing images...", 4)
    items = []
    for item in results.get('itemSummaries', []):
        card = {'title': item.get('title', 'no_title')}
        image_url = item.get('image', {}).get('imageUrl')
        if image_url:
            card['image'] = bytearray(spinarak.download_image(image_url, card['title'], INPUT_DIR, USE_LOCAL_STORAGE))
        else:
            miscellaneous.print_with_color(f"No image found for: {card['title']}", 1)
        items.append(card)

    miscellaneous.print_with_color("Listed Images have been downloaded! 🥳", 2)
    miscellaneous.pause(10)

    for item in items:
        miscellaneous.print_with_color(f"Processing {item['title']}...", 4)
        image = None
        path = ''
        if USE_LOCAL_STORAGE:
            image, path = smeargle.load_file_from_directory(item['title'], INPUT_DIR, OUTPUT_DIR)
        else:
            image, path = smeargle.load_file_from_bytearray(item.get('image', None), item.get('title', 'no_title'))
        image_edges = smeargle.detect_edges(image, path)

        approx = smeargle.detect_contours(image_edges)
        if len(approx) != 4:
            miscellaneous.print_with_color(f"Skipping '{item['title']}' — could not detect card corners.", 3)
            continue

        aligned = smeargle.draw_contours(image, approx, path, CARD_DIM)
        roi = smeargle.roi_extraction(aligned, path, ROI_BOX)
        miscellaneous.print_with_color(f"Finished Processing {item['title']}", 2)

    miscellaneous.pause(10)

if __name__ == "__main__":
    args = miscellaneous.pass_arguments_to_main()
    main(args.defect, args.use_local_storage, args.use_rgb, args.kaggle_download)