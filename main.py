import spinarak
import smeargle
import porygon
import miscellaneous

def main(defect: str, threshold: float, USE_LOCAL_STORAGE: bool, USE_RGB: bool, download_dataset: bool, AI: porygon.models.Sequential | None = None, verbose: bool = False):
    args = miscellaneous.parse_JSON_as_arguments('config.json', defect,
        [
            "input_shape",
            "dataset",
            "num_classes",
            "dimensions",
            "roi",
            "input_dir",
            "debugging_dir",
            "training_dir",
            'query'
        ]
    )
    author, dataset_name = args.get('dataset', []).split("/")

    miscellaneous.clear_terminal()

    if not AI:
        directoryCheck = miscellaneous.directory_check(args.get("training_dir", ""))
        attempts = 3
        while not directoryCheck:
            if attempts < 0:
                exit()
            args.update({
                'training_dir': porygon.get_dataset(
                    args.get("training_dir", ""),
                    author,
                    dataset_name,
                    download_dataset,
                    USE_LOCAL_STORAGE
                )})
            attempts -= 1
            directoryCheck = miscellaneous.directory_check(args.get("training_dir", ""))

        images, labels, filenames = porygon.load_dataset_from_directory(args.get("training_dir", ""), args.get('input_shape', ''), USE_RGB)
        if verbose: porygon.display_sample(images, labels, filenames)
        new_images, new_labels = porygon.convert_and_reshape(images, labels)
        training_images, testing_images, training_labels, testing_labels = porygon.split_dataset(new_images, new_labels)
    
        AI = porygon.build_model(args.get('num_classes', ''), USE_RGB)
        porygon.train_model(AI, training_images, training_labels)
        porygon.evaluate_model(AI, testing_images, testing_labels)
        porygon.predict_and_visualize(AI, testing_images, testing_labels, USE_RGB, testing=True)

    CLIENT_ID, CLIENT_SECRET = miscellaneous.enviromentals('EBAY_CLIENT_ID', 'EBAY_CLIENT_SECRET')

    miscellaneous.print_with_color("Authenticating with eBay...", 4)
    token = spinarak.get_ebay_token(CLIENT_ID, CLIENT_SECRET)

    items = []

    itemIds = miscellaneous.load_itemIds_from_file()
    for query in args.get('query', []):
        miscellaneous.print_with_color(f"Searching for Pokémon card listings '{query}'...", 4)
        results = spinarak.search_pokemon_cards(token, price=threshold, query='')

        miscellaneous.print_with_color("Downloading listing images...", 4)

        for item in results.get('itemSummaries', []):
            if item.get('itemId', '') in itemIds: continue
            card = {
                'title': item.get('title', ''),
                'product_url': item.get('itemWebUrl', ''),
                'image_url': item.get('image', {}).get('imageUrl', '')
            }
        
            if card['image_url']:
                card['image'] = bytearray(spinarak.download_image(card['image_url'], card['title'], args.get('input_dir', ''), USE_LOCAL_STORAGE))
                items.append(card)
                continue
            miscellaneous.print_with_color(f"No image found for: {card['title']}", 1)
            

    miscellaneous.print_with_color("Listed Images have been downloaded! 🥳", 2)
    miscellaneous.pause(10)

    rois = []
    for item in items:
        miscellaneous.print_with_color(f"Processing {item['title']}...", 4)
        image = None
        path = ''
        if USE_LOCAL_STORAGE:
            image, path = smeargle.load_file_from_directory(item['title'], args.get('input_dir', ''), args.get('debugging_dir', ''))
        else:
            image, path = smeargle.load_file_from_bytearray(item.get('image', bytearray()), item.get('title', 'no_title'))
        image_edges = smeargle.detect_edges(image, path)

        approx = smeargle.detect_contours(image, image_edges)

        if len(approx) != 4:
            miscellaneous.print_with_color(f"Skipping '{item['title']}' — could not detect card corners.", 3)
            items.remove(item['title'])
            continue

        aligned = smeargle.draw_contours(image, approx, path, args.get('dimensions', ''))
        roi = smeargle.roi_extraction(aligned, path, args.get('roi', ''))
        rois.append(porygon.cv2.resize(roi, args.get('input_shape', '')))
        item.pop('image')
        miscellaneous.print_with_color(f"Finished Processing {item['title']}", 2)

    truth_values = porygon.predict_and_visualize(AI, porygon.np.array(rois), USE_RGB=USE_RGB)

    for truth_value, card in zip(truth_values, items):
        card['truth'] = False
        if truth_value == 0:
            card.update({'truth': True})

    miscellaneous.pause(5)
    return items

if __name__ == "__main__":
    args = miscellaneous.pass_arguments_to_main()
    main(args.defect, args.price, args.use_local_storage, args.use_rgb, args.kaggle_download)