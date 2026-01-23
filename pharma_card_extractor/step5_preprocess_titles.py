import os
from pathlib import Path
from PIL import Image, ImageOps

INPUT_DIR = "check_titles_dir"
OUTPUT_DIR = "titles_preprocessed"
CONTENT_THRESHOLD = 240
PADDING_X, PADDING_Y = 20, 6

Image.MAX_IMAGE_PIXELS = None


def get_manual_bbox(img_gray, threshold):
    # 计算内容包围盒并屏蔽边缘噪点
    width, height = img_gray.size
    binary = img_gray.point(lambda p: 255 if p < threshold else 0)
    edge_margin = 15

    if width <= 2 * edge_margin or height <= 2 * edge_margin:
        return binary.getbbox()

    clean_binary = Image.new("L", (width, height), 0)
    box = (edge_margin, edge_margin, width - edge_margin, height - edge_margin)
    clean_binary.paste(binary.crop(box), box)
    return clean_binary.getbbox()


def process_single_image(img_path, output_dir):
    try:
        with Image.open(img_path) as img:
            gray = img.convert("L")
            bbox = get_manual_bbox(gray, CONTENT_THRESHOLD)
            if not bbox: return

            left, top, right, bottom = bbox
            new_box = (max(0, left - PADDING_X), max(0, top - PADDING_Y),
                       min(gray.width, right + PADDING_X), min(gray.height, bottom + PADDING_Y))

            cropped = gray.crop(new_box)
            ImageOps.autocontrast(cropped, cutoff=0).save(output_dir / img_path.name)
    except Exception as e:
        print(f"处理失败 {img_path.name}: {e}")


def main():
    input_path, output_path = Path(INPUT_DIR), Path(OUTPUT_DIR)
    if not input_path.exists(): return
    output_path.mkdir(parents=True, exist_ok=True)

    files = sorted(list(input_path.glob("*.png")), key=lambda f: int(f.stem) if f.stem.isdigit() else 0)
    for f in files:
        process_single_image(f, output_path)


if __name__ == "__main__":
    main()