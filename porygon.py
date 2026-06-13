# Porygon
# Embedding encoder, gallery loading, card retrieval, and ROI misprint inference
# for PokéPrint Inspector.

from torchvision.transforms import Compose, ToTensor, Normalize, Resize, ToPILImage
from torch.nn import Module as NNM
from spinarak import run as spinarak
from rotom import (
    env,
    sanitize_filename,
    show_image,
    save_image,
    module_arguments,
    configure_logger,
    push_dataset_to_kaggle,
)
from cv2.typing import MatLike as MAT
from numpy.typing import NDArray as NPA

import os
import cv2
import numpy as np
import torch
import timm
import yaml
import json
import logging
import random

_NAME = "porygon"
_KAGGLE_ARTIFACT = os.path.join(env("KAGGLE_ARTIFACT", "kaggle")[0])

_MAX_FALSES = int(env("MAX_FALSES", "5")[0])
_INPUT_DIR = env("INPUT_DIR", os.path.join(".", "input"))[0]
_OUTPUT_DIR = env("IMAGE_DEBUG_DIR", os.path.join(".", "output"))[0]
_DATASET_DIR = env("PORYGON_DATASET_DIR", os.path.join("datasets", "gallery"))[0]
_GALLERY_DIR = os.path.join(_KAGGLE_ARTIFACT, env("GALLERY_DIR", "gallery")[0])
_EMBEDDINGS_FILE = "embeddings.npz"
_METADATA_FILE = "metadata.json"
_SAMPLE_SIZE = int(env("SAMPLE_SIZE", "50")[0])

TILE_SIZE = (200, 280)
BORDER = 4
TEXT_HEIGHT = 30


def _get_porygon_config(config: dict | None) -> dict:
    """Accept either the full app config or the porygon-scoped config."""
    if not isinstance(config, dict):
        return {}
    return config.get(_NAME, config.get("porygon", config))


def _get_cards_config(config: dict | None) -> dict:
    return _get_porygon_config(config).get("cards", {})


def _get_aligned_dimensions(config: dict | None, card_id: str | None = None) -> tuple[int, int]:
    porygon_cfg = _get_porygon_config(config)
    dims = porygon_cfg.get("aligned_dimensions", [960, 1360])
    if card_id:
        card_cfg = _get_cards_config(config).get(card_id, {})
        dims = card_cfg.get("aligned_dimensions", dims)
    return int(dims[0]), int(dims[1])


def _load_canonical(card_id: str) -> MAT | None:
    """Load canonical from packaged gallery first, then fall back to dataset folder."""
    candidates = [
        os.path.join(_GALLERY_DIR, "canonicals", f"{card_id}.jpg"),
        os.path.join(_GALLERY_DIR, "canonicals", f"{card_id}.png"),
        os.path.join(_DATASET_DIR, card_id, "canonical.jpg"),
        os.path.join(_DATASET_DIR, card_id, "canonical.png"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return cv2.imread(path, cv2.IMREAD_COLOR)
    return None


def _load_data_from_directory(path: str, qa: bool = False) -> list[tuple[MAT, str, str]]:
    """
    Load labeled images from a directory. Filenames should end with __<int_label>.
    This is build/manual tooling, not the main inference path.
    """
    logger = logging.getLogger(_NAME)
    logger.debug(f"Loading dataset from '{path}'...")
    filenames: list[str] = []
    ret: list[tuple[MAT, str, str]] = []

    if not path or not os.path.isdir(path):
        raise Exception(f"'{path}' is not a directory.")

    try:
        for root, _, files in os.walk(path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in (".jpg", ".jpeg", ".png"):
                    filenames.append(os.path.join(root, file))
    except Exception as e:
        logger.exception(f"Error accessing directory '{path}': {e}")

    if len(filenames) < _SAMPLE_SIZE:
        raise Exception(f"{path} has too few images!")

    for filepath in filenames:
        img = cv2.imread(filepath, cv2.IMREAD_COLOR)
        if img is None:
            logger.warning(f"Unable to read image: {filepath}. Skipping...")
            continue

        label = os.path.splitext(filepath)[0].rsplit("__", 1)[-1] if "__" in filepath else ""
        if not label.isdigit():
            logger.warning(f"'{filepath}' does not contain a valid integer label. Skipping...")
            continue

        ret.append((img, label, filepath))

    if qa:
        return random.sample(ret, min(_SAMPLE_SIZE, len(ret))) if ret else []
    return ret


def generate(qa: bool = False, progress: bool = False, debug: bool = False):
    """Manual helper for building a gallery dataset. Not used by runtime inference."""
    debug = debug or qa or progress
    configure_logger(_NAME, debug=debug)
    logger = logging.getLogger(_NAME)

    if progress:
        if not os.path.isdir(_DATASET_DIR):
            raise Exception(f"'{_DATASET_DIR}' does not exist")

        entries: dict[str, dict[str, int]] = {}
        for root, dirs, _ in os.walk(_DATASET_DIR):
            for dir_name in dirs:
                normal = misprints = 0
                files = os.listdir(os.path.join(root, dir_name))
                for file in files:
                    if file.endswith(".jpg"):
                        filename = os.path.splitext(file)[0]
                        label = filename.rsplit("__", 1)[-1] if "__" in filename else "unknown"
                        if label == "0":
                            normal += 1
                        elif label != "unknown":
                            misprints += 1
                entries[dir_name] = {"normal": normal, "misprints": misprints, "total": len(files)}

        logger.debug(
            "Dataset progress:\n"
            + "\n".join(
                [
                    f"  {dir}: {data['normal']} normal, {data['misprints']} misprints, {data['total']} total"
                    for dir, data in entries.items()
                ]
            )
        )
        return

    queries = ["Wartortle 42/102"]
    limit = 300
    input_dir = _DATASET_DIR if qa else _INPUT_DIR

    if not os.path.isdir(input_dir) or len(os.listdir(input_dir)) < _SAMPLE_SIZE:
        logger.warning(f"{input_dir} has too few images. Running Spinarak to populate it...")
        spinarak(debug=True, queries=queries, limit=limit)

    if not input_dir or not os.path.isdir(input_dir):
        raise Exception(f"Input directory '{input_dir}' does not exist or is not a directory.")

    rejects: list[str] = []
    for image, label, file in _load_data_from_directory(input_dir):
        try:
            file = sanitize_filename(file)
            normal_exist_path = os.path.isfile(os.path.join(_DATASET_DIR, f"0__{file}"))
            misprint_exist_path = os.path.isfile(os.path.join(_DATASET_DIR, f"1__{file}"))
            reject_exist_path = os.path.isfile(os.path.join(_DATASET_DIR, f"2__{file}"))

            if not qa and (reject_exist_path or normal_exist_path or misprint_exist_path):
                logger.info(f"Skipping '{file}' because it has already been processed.")
                continue

            choice = show_image(image, _NAME)
            if choice is None:
                logger.debug(f"User skipped '{file}'")
                if qa and label != "2":
                    rejects.append(file)
                if debug:
                    save_image(image, os.path.join(_OUTPUT_DIR, file), "skipped")
            elif not choice:
                logger.debug(f"User identified '{file}' as a misprint")
                if qa and label != "1":
                    rejects.append(file)
                if debug:
                    save_image(image, os.path.join(_OUTPUT_DIR, file), "rejected")
            else:
                logger.debug(f"User identified '{file}' as a normal print")
                if qa and label != "0":
                    rejects.append(file)
                if debug:
                    save_image(image, os.path.join(_OUTPUT_DIR, os.path.splitext(file)[0]), "accepted")

            out_label = "0" if choice else "1" if choice is not None else "2"
            if not qa:
                save_image(image, os.path.join(_DATASET_DIR, file), out_label, sep="__")
            elif len(rejects) >= _MAX_FALSES:
                logger.warning("Too many rejections during QA. Stopping process.")
                break

        except Exception as e:
            logger.warning(f"Failed to process '{file}': {e}")

    if qa:
        logger.debug(f"QA results: {len(rejects)} rejected")
        logger.warning("Rejected files: " + ", ".join(rejects))


def _create_yaml_and_json():
    paths = {
        "embeddings_file": _EMBEDDINGS_FILE,
        "metadata_file": _METADATA_FILE,
    }
    with open("config.json", "r") as f:
        config: dict = json.load(f)

    os.makedirs(_DATASET_DIR, exist_ok=True)
    with open(os.path.join(_DATASET_DIR, "dataset.yaml"), "w") as f:
        yaml.dump(paths, f, default_flow_style=False, sort_keys=False)
    with open(os.path.join(_DATASET_DIR, "config.json"), "w") as f:
        json.dump(config, f, indent=4)


def push(message: str):
    logger = logging.getLogger(_NAME)
    _create_yaml_and_json()
    res = push_dataset_to_kaggle(os.path.abspath(_DATASET_DIR), message)
    if res.returncode == 0:
        logger.debug("Dataset pushed to Kaggle successfully.")
    else:
        logger.error(f"Failed to push dataset to Kaggle: {res.stdout} {res.stderr}")


def load_gallery(gallery: str | None | dict = None) -> dict:
    """Load embeddings.npz and metadata.json from a gallery directory, or return provided gallery dict."""
    if isinstance(gallery, dict):
        return gallery

    gallery_dir = gallery if isinstance(gallery, str) else _GALLERY_DIR
    embeddings_path = os.path.join(gallery_dir, _EMBEDDINGS_FILE)
    metadata_path = os.path.join(gallery_dir, _METADATA_FILE)

    gallery_arrays = np.load(embeddings_path)
    with open(metadata_path, "r") as f:
        gallery_meta: dict = json.load(f)

    return {"embeddings": gallery_arrays, "metadata": gallery_meta}


def _retrieve_similar(query_embedding: NPA, embeddings: NPA, metadata: list[dict], k: int = 5) -> list[dict]:
    sims = embeddings @ query_embedding
    ranked = np.argsort(sims)[::-1]

    results = []
    for idx in ranked:
        entry = dict(metadata[idx])
        entry["similarity"] = float(sims[idx])
        results.append(entry)
        if len(results) >= k:
            break

    return results


def _predict_defect_probability(query_embedding: NPA, weight: NPA, bias: NPA) -> float:
    score = float(query_embedding @ weight + bias[0])
    return float(1.0 / (1.0 + np.exp(-score)))


def _make_tile(img: MAT, label: str, border_color: tuple, tile_size: tuple[int, int], T: int, text_h: int) -> MAT:
    W, H = tile_size
    tile_h = H + text_h
    tile = cv2.resize(img, (W, H))
    tile = cv2.copyMakeBorder(tile, T, T, T, T, cv2.BORDER_CONSTANT, value=border_color)
    canvas = np.zeros((tile_h + T * 2, W + T * 2, 3), dtype=np.uint8)
    canvas[: H + T * 2, :] = tile
    cv2.putText(canvas, label[:46], (4, H + T * 2 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (245, 245, 245), 1, cv2.LINE_AA)
    return canvas


def _visualize_results(query_img: MAT, results: list[dict], title: str = "Retrieval") -> None:
    logger = logging.getLogger(_NAME)
    W, H = TILE_SIZE
    tiles = [_make_tile(query_img, "QUERY", (0, 200, 0), (W, H), BORDER, TEXT_HEIGHT)]

    for r in results:
        path = r.get("image_path", "")
        img = cv2.imread(path, cv2.IMREAD_COLOR) if path and os.path.isfile(path) else np.full((H, W, 3), 40, dtype=np.uint8)
        if img is None:
            logger.warning(f"Failed to load image for visualization: {path}")
            img = np.full((H, W, 3), 40, dtype=np.uint8)

        sim = r.get("similarity", 0.0)
        label = r.get("label", "?")
        label_name = r.get("label_name", "")
        name = os.path.basename(path)
        text = f"{name} L={label}:{label_name} {sim:.3f}"

        sim_clamped = max(0, min(1, sim))
        g = int(255 * sim_clamped)
        red = int(255 * (1 - sim_clamped))
        tiles.append(_make_tile(img, text, (0, g, red), (W, H), BORDER, TEXT_HEIGHT))

    for start in range(0, len(tiles), 5):
        show_image(np.hstack(tiles[start : start + 5]), title)


def build_encoder(encoder: NNM | None = None, config: dict | None = None) -> tuple[NNM, Compose, str]:
    """Build or normalize the shared Porygon encoder from config["porygon"]["encoder"]."""
    logger = logging.getLogger(_NAME)
    encoder_cfg = _get_porygon_config(config).get("encoder", {})

    model_name = encoder_cfg["model"]
    img_size = int(encoder_cfg["image_size"])
    mean = encoder_cfg["imagenet_mean"]
    std = encoder_cfg["imagenet_std"]

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    transform = Compose([
        ToPILImage(),
        Resize((img_size, img_size)),
        ToTensor(),
        Normalize(mean=mean, std=std),
    ])

    if encoder is None:
        logger.debug(f"Building encoder '{model_name}' on device '{dev}'...")
        encoder = timm.create_model(model_name, pretrained=True, num_classes=0)

    encoder.eval()
    encoder.to(dev)
    for param in encoder.parameters():
        param.requires_grad = False

    logger.debug("Encoder ready. All weights frozen.")
    return encoder, transform, dev


def _embed_batch(imgs: list[MAT], encoder: NNM, transform: Compose, device: str) -> np.ndarray:
    if not imgs:
        return np.empty((0, 0), dtype=np.float32)

    batches = []
    batch_size = 32
    for start in range(0, len(imgs), batch_size):
        batch = imgs[start : start + batch_size]
        tensors = torch.stack([
            torch.as_tensor(transform(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
            for img in batch
        ]).to(device)

        with torch.no_grad():
            feats = encoder(tensors).cpu().numpy()

        norms = np.linalg.norm(feats, axis=1, keepdims=True)
        batches.append((feats / np.maximum(norms, 1e-8)).astype(np.float32))

    return np.vstack(batches)


def _embed_one(img: MAT, encoder: NNM, transform: Compose, device: str) -> np.ndarray:
    return _embed_batch([img], encoder, transform, device)[0]


def _identify_card(img: MAT, gallery: dict, enc: NNM, trans: Compose, dev: str) -> tuple[str, list[dict]]:
    arrays = gallery["embeddings"]
    meta = gallery["metadata"]
    id_info = meta["identification"]

    query_embedding = _embed_one(img, enc, trans, dev)
    embeddings = arrays[id_info["embedding_key"]]
    results = _retrieve_similar(query_embedding, embeddings, id_info["metadata"])

    predicted_card = results[0]["card_id"] if results else ""
    return predicted_card, results


def _extract_aligned_roi(
    image: MAT,
    canonical: MAT,
    roi_box: tuple[int, ...],
    output_size: tuple[int, int],
    min_matches: int = 12,
):
    if image is None or canonical is None:
        return None, None, None, 0

    canonical = cv2.resize(canonical, output_size)

    gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_ref = cv2.cvtColor(canonical, cv2.COLOR_BGR2GRAY)

    orb = getattr(cv2, "ORB_create")(nfeatures=1000)
    kp_img, des_img = orb.detectAndCompute(gray_img, None)
    kp_ref, des_ref = orb.detectAndCompute(gray_ref, None)

    if des_img is None or des_ref is None:
        return None, None, None, 0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw_matches = matcher.knnMatch(des_img, des_ref, k=2)

    good: list[cv2.DMatch] = []
    for pair in raw_matches:
        if len(pair) != 2:
            continue
        m, n = pair
        if m.distance < 0.75 * n.distance:
            good.append(m)

    if len(good) < min_matches:
        return None, None, None, len(good)

    good = sorted(good, key=lambda x: x.distance)

    src_pts = np.array([kp_img[m.queryIdx].pt for m in good], dtype=np.float32).reshape(-1, 1, 2)
    dst_pts = np.array([kp_ref[m.trainIdx].pt for m in good], dtype=np.float32).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None, None, None, len(good)

    aligned = cv2.warpPerspective(image, H, output_size)
    x, y, w, h = roi_box
    roi = aligned[y : y + h, x : x + w]

    if roi.size == 0:
        return None, aligned, H, int(mask.sum()) if mask is not None else len(good)

    return roi, aligned, H, int(mask.sum()) if mask is not None else len(good)


def _defect_status(prob: float, suspicious: float, likely: float) -> str:
    if prob >= likely:
        return "likely_misprint"
    if prob >= suspicious:
        return "suspicious"
    return "normal"


def _identify_misprints(
    img: MAT,
    card_id: str,
    gallery: dict,
    enc: NNM,
    trans: Compose,
    dev: str,
    config: dict,
) -> tuple[dict, list[dict]]:
    arrays = gallery["embeddings"]
    meta = gallery["metadata"]

    output_size = _get_aligned_dimensions(config, card_id)
    canonical = _load_canonical(card_id)
    if canonical is None:
        raise Exception(f"No canonical found for {card_id}")

    outputs: list[dict] = []
    card_defects = meta.get("defects", {}).get(card_id, {})
    suspected_labels: set[str] = set()

    for misprint_name, regions in card_defects.items():
        for region_name, region_info in regions.items():
            roi_box = tuple(region_info["roi_box"])
            roi, aligned, H_mat, inliers = _extract_aligned_roi(
                image=img,
                canonical=canonical,
                roi_box=roi_box,
                output_size=output_size,
            )

            if roi is None:
                outputs.append({
                    "card_id": card_id,
                    "misprint": misprint_name,
                    "label": str(region_info.get("target_label", "")),
                    "region": region_name,
                    "status": "roi_extraction_failed",
                    "probability": None,
                    "inliers": int(inliers),
                })
                continue

            roi_embedding = _embed_one(roi, enc, trans, dev)
            weight = arrays[region_info["weight_key"]]
            bias = arrays[region_info["bias_key"]]

            prob = _predict_defect_probability(roi_embedding, weight, bias)
            thresholds = region_info["thresholds"]
            status = _defect_status(
                prob,
                suspicious=float(thresholds["suspicious"]),
                likely=float(thresholds["likely_misprint"]),
            )

            target_label = str(region_info.get("target_label", ""))
            if status in ("suspicious", "likely_misprint") and target_label:
                suspected_labels.add(target_label)

            outputs.append({
                "card_id": card_id,
                "misprint": misprint_name,
                "region": region_name,
                "probability": prob,
                "status": status,
                "inliers": int(inliers),
                "roi": roi,
            })

    probs = [o["probability"] for o in outputs if o.get("probability") is not None]
    conclusion = {
        "card_id": card_id,
        "labels": sorted(suspected_labels) if suspected_labels else ["0"],
        "prob": float(np.mean(probs)) if probs else None,
    }
    return conclusion, outputs


def _embed(img: MAT, enc: NNM, trans: Compose, dev: str) -> NPA:
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    tensor = trans(rgb)
    if not isinstance(tensor, torch.Tensor):
        tensor = torch.from_numpy(tensor)
    tensor = tensor.unsqueeze(0).to(dev)

    with torch.no_grad():
        feats: torch.Tensor = enc(tensor)

    vec: np.ndarray = feats.squeeze(0).cpu().numpy()
    norm = np.linalg.norm(vec)
    return vec / max(norm, 1e-8)


def health(img: MAT, gallery: dict, enc: NNM | None, config: dict, target_conclusion: dict) -> tuple[list[str], list[bool]]:
    configure_logger(_NAME, debug=True)
    logger = logging.getLogger(_NAME)
    checklist: list[str] = []
    checks: list[bool] = []
    trans = None
    dev = None
    card_id = ""
    conclusion = None
    config = config[_NAME]

    checklist.append("Embeddings was successfully loaded from disk")
    try:
        gallery = load_gallery(gallery)
        checks.append("embeddings" in gallery and "metadata" in gallery)
    except Exception as e:
        logger.error(f"Failed to load gallery: {e}")
        checks.append(False)

    checklist.append("Encoder was successfully built and can process images")
    try:
        enc, trans, dev = build_encoder(enc, config=config)
        test_emb = _embed(img, enc, trans, dev)
        expected_dim = int(_get_porygon_config(config)["encoder"]["embedding_dimension"])
        checks.append(test_emb.shape == (expected_dim,))
    except Exception as e:
        logger.error(f"Failed to build encoder or embed test image: {e}")
        checks.append(False)

    checklist.append("Similar card retrieval returns results with expected structure")
    try:
        if gallery is None or enc is None or trans is None or dev is None:
            raise Exception("Gallery or encoder not properly initialized.")
        card_id, id_results = _identify_card(img, gallery, enc, trans, dev)
        st = isinstance(id_results, list) and all(isinstance(r, dict) for r in id_results)
        if not st:
            logger.warning(f"Identification results have unexpected structure: {id_results}")
        checks.append(st)
    except Exception as e:
        logger.error(f"Failed to retrieve similar cards: {e}")
        checks.append(False)

    checklist.append("Misprint identification returns results with expected structure")
    try:
        if gallery is None or enc is None or trans is None or dev is None:
            raise Exception("Gallery or encoder not properly initialized.")
        conclusion, misprint_results = _identify_misprints(img, card_id, gallery, enc, trans, dev, config)
        st = isinstance(misprint_results, list) and all(isinstance(r, dict) for r in misprint_results)
        if not st:
            logger.warning(f"Misprint results have unexpected structure: {misprint_results}")
        checks.append(st)
    except Exception as e:
        logger.error(f"Failed to identify misprints: {e}")
        checks.append(False)

    checklist.append("The predicted conclusion matches the expected conclusion for the test image")
    try:
        if conclusion is None:
            raise Exception("Conclusion was not generated.")
        conclusion_no_prob = {k: v for k, v in conclusion.items() if k != "prob"}
        target_no_prob = {k: v for k, v in target_conclusion.items() if k != "prob"}
        st = conclusion_no_prob == target_no_prob
        if not st:
            logger.warning(f"Got {conclusion_no_prob}, expected {target_no_prob}")
        checks.append(st)
    except Exception as e:
        logger.error(f"Failed to compare conclusion with target: {e}")
        checks.append(False)

    return checklist, checks


def run(**kwargs):
    debug = kwargs.get("debug", False)
    gallery = load_gallery(kwargs.get("model", None))
    config = kwargs.get("config", {})[_NAME]
    enc, trans, dev = build_encoder(kwargs.get("encoder", None), config=config)
    imgs: list[MAT] = kwargs.get("data", [])

    configure_logger(_NAME, debug=debug)
    logger = logging.getLogger(_NAME)
    logger.debug(f"Starting {_NAME}...")

    all_results = []
    for img in imgs:
        if img is None:
            logger.warning("Received None image in data. Skipping.")
            continue

        predicted_card, id_results = _identify_card(img, gallery, enc, trans, dev)
        if not predicted_card:
            all_results.append(({"card_id": "", "labels": ["0"], "prob": None}, []))
            continue

        results = _identify_misprints(img, predicted_card, gallery, enc, trans, dev, config)
        all_results.append(results)

    return all_results


def main():
    args = module_arguments(
        desc="Porygon: Pokémon card embedding and misprint inference module.",
        subcommands={
            "generate": {
                "desc": "Process raw images to generate a labeled gallery dataset.",
                "args": {
                    "--qa": {"action": "store_true", "help": "Sample a subset of images for manual review."},
                    "--debug": {"action": "store_true", "help": "Save intermediate images"},
                    "--progress": {"action": "store_true", "help": "Show dataset generation progress"},
                },
            },
            "push": {
                "desc": "Push gallery dataset to Kaggle.",
                "args": {"--message": {"type": str, "help": "Commit message", "default": ""}},
            },
            "run": {
                "desc": "Runtime inference entrypoint placeholder.",
                "args": {
                    "--path": {"type": str, "help": "Path to raw images folder", "default": _INPUT_DIR},
                    "--debug": {"action": "store_true", "help": "Enable debug logging"},
                },
            },
        },
    )

    if not hasattr(args, "command") or args.command is None:
        print("No command provided. Use --help for usage information.")
        return
    if args.command == "generate":
        generate(args.qa, args.progress, args.debug)
    elif args.command == "push":
        push(args.message)
    elif args.command == "run":
        pass


if __name__ == "__main__":
    main()
