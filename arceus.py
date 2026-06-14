from spinarak import run as spinarak, health as spinarak_health
from smeargle import run as smeargle, health as smeargle_health, load_yolo_model
from porygon import run as porygon, health as porygon_health, load_gallery, build_encoder
from rotom import configure_logger, load_config, module_arguments, cv2, np, postgresql, env
from time import sleep

import logging

_NAME = "arceus"

def _load_essentials():
    logger = logging.getLogger(_NAME)

    logger.debug("Loading configuration...")
    config = load_config(_NAME)
    logger.debug("Configuration loaded")

    logger.debug("Loading YOLO model...")
    yolo_model = load_yolo_model()
    logger.debug("YOLO model loaded successfully.")

    logger.debug("Loading gallery...")
    gallery = load_gallery()
    logger.debug("Gallery loaded successfully.")

    logger.debug("Building encoder...")
    enc, _, _ = build_encoder()
    logger.debug("Encoder built successfully.")

    return config, yolo_model, gallery, enc

def _save_to_database(card_details: list[dict]):
    logger = logging.getLogger(_NAME)
    for detail in card_details:
        logger.warning(f"card similarity: {detail.get('similarity', 'N/A')}, misprint: {detail.get('misprint', 'N/A')}, certainty: {detail.get('certainty', 'N/A')}")
        postgresql("INSERT INTO {{tables}} ({{columns}}) VALUES ({{values}})", 
            env('POSTGRESQL_TABLE_FOR_REPORTS'),
            ('id', 'market_id', 'card', 'misprint', 'url', 'image', 'certainty'),
            {
                'id': detail['id'],
                'market_id': detail['itemId'],
                'card': detail['card'],
                'misprint': detail['misprint'],
                'url': detail['url'],
                'image': detail['image_url'],
                'certainty': detail['certainty'],
            }
        )
    logger.debug(f"Saved {len(card_details)} suspected cards to the database.")
    

def health(raw_image: bytearray|None = None, image_name: str = '') -> tuple[list[str], list[bool]]:
    configure_logger(_NAME, debug=True)
    logger = logging.getLogger(_NAME)
    checklist: list[str] = []
    check: list[bool] = []
    config = {}
    image: np.ndarray | None = None
    card_name = image_name.split("/")[-1].split(".")[0].rsplit("_", maxsplit=1)[0]
    
    checklist.append("Loaded configuration")
    try:
        config = load_config(_NAME)
        check.append(True)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        check.append(False)

    spinarak_status = spinarak_health()
    checklist.extend(spinarak_status[0])
    check.extend(spinarak_status[1])

    if raw_image is None:
        logger.warning("Smeargle and Porygon health checks were skipped because no test image was provided.")
        return checklist, check

    smeargle_status = smeargle_health([raw_image])
    checklist.extend(smeargle_status[0])
    check.extend(smeargle_status[1])

    checklist.append("Read test image into OpenCV format")
    try:
        if raw_image is None:
            raise Exception("No image data to read")
        image_bytes = np.frombuffer(raw_image, dtype=np.uint8)
        image = cv2.imdecode(image_bytes, cv2.IMREAD_COLOR)
        if image is not None:
            check.append(True)
        else:
            logger.error("Failed to decode image with OpenCV")
            check.append(False)
    except Exception as e:
        logger.error(f"Failed to read test image: {e}")
        check.append(False)
    
    conclusion = {
        "card_id": card_name,
        "labels": image_name.split("/")[-1].split(".")[0].rsplit("_", maxsplit=1)[1].split("__"),
    }

    if image is not None:
        porygon_status = porygon_health(image, config=config, target_conclusion=conclusion)
        checklist.extend(porygon_status[0])
        check.extend(porygon_status[1])

    return checklist, check
    
def run(**kwargs):
    debug: bool = kwargs.get("debug", False)
    configure_logger(_NAME, debug=debug)
    logger = logging.getLogger(_NAME)

    logger.debug(f"Starting {_NAME}...")

    config, yolo_model, gallery, enc = _load_essentials()

    while True:
        suspected_cards = []
        for card_id, card_cfg in config['cards'].items():
            logger.debug(f"Processing card: {card_id}")

            spinarak_cfg = {}
            spinarak_cfg['config'] = load_config("spinarak", card_cfg)
            logger.debug("Running Spinarak...")
            card_details = spinarak(**spinarak_cfg, debug=debug)

            smeargle_cfg = {}
            smeargle_cfg['config'] = load_config("smeargle", config)
            smeargle_cfg['model'] = yolo_model
            card_images: list[bytearray] = [d['image'] for d in card_details]
            logger.debug("Running Smeargle...")
            crop_details = smeargle(**smeargle_cfg, imgs=card_images, debug=debug)

            for crop_detail in crop_details:
                source_idx: int = crop_detail['source_idx']
                if 'crop' not in crop_detail or crop_detail['crop'] is None:
                    logger.warning(f"No crop source index {source_idx}.")
                    continue
                card_details[source_idx]['crop'] = crop_detail['crop']

            # remove any card details that don't have crops for Porygon
            card_details = [d for d in card_details if 'crop' in d and d['crop'] is not None]
            if not card_details:
                logger.warning("No valid crops found for any card details. Skipping Porygon.")
                continue
            porygon_cfg = {}
            porygon_cfg['config'] = config
            porygon_cfg['encoder'] = enc
            porygon_cfg['gallery'] = gallery
            crop_images: list = [d['crop'] for d in card_details]
            logger.debug("Running Porygon...")
            results = porygon(**porygon_cfg, imgs=crop_images, debug=debug)

            assert len(results) == len(card_details), "Number of conclusions and card details must match"

            for result, detail in zip(results, card_details):
                concl = result[0]
                if 'misprints' not in concl: continue
                for misprint, summary in concl['misprints'].items():
                    if summary["status"] in ["likely_misprint", "suspicious"]:
                        detail['misprint'] = misprint
                        detail['certainty'] = summary["prob"]
                        detail['card'] = concl['card_id']
                        detail['similarity'] = concl['card_similarity']
            # Only keep details that have a misprint flagged
            card_details = [d for d in card_details if 'misprint' in d]
            suspected_cards.extend(card_details)
        _save_to_database(suspected_cards)
        break  # Remove this break to run continuously
                
def main():
    args = module_arguments(
        desc="""
        Arceus is the master module that orchestrates the entire misprint detection pipeline.
        It integrates Spinarak for eBay data extraction, Smeargle for image processing, and Porygon for misprint classification.
        The module continuously monitors specified cards and flags any suspicious findings based on configurable thresholds.
        """,
        subcommands={
            "health": {
                "desc": "Check the health of all submodules (Spinarak, Smeargle, Porygon) and their dependencies.",
            },
            "run": {
                "desc": "Run the full misprint detection pipeline in a continuous loop, processing specified cards and flagging suspicious findings.",
                "args": {
                    "--debug": {
                        "action": "store_true",
                        "help": "Enable debug logging for detailed output.",
                    },
                },
            },
        }
    )
    if not hasattr(args, "command") or args.command is None:
        print("No command provided. Use --help for more information.")
        return
    if args.command == "health":
        health_status = health()
        print("Health Status:")
        for module, status in zip(health_status[0], health_status[1]):
            print(f"{module}: {'OK' if status else 'FAIL'}")
    elif args.command == "run":
        run(debug=args.debug)

if __name__ == "__main__":
    main()