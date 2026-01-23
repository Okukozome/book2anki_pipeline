import os
import numpy as np
from PIL import Image
from pathlib import Path

INPUT_DIR = "raw_pages_dir"
OUTPUT_DIR_CLEAN = "cropped_pages_clean"
OUTPUT_DIR_TRICOLOR = "cropped_pages_tricolor"

# 奇偶页不同的裁剪区域
ODD_PAGE_CROP_BOX = (376, 255, 2197, 3120)
EVEN_PAGE_CROP_BOX = (274, 255, 2095, 3120)

COLOR_BLACK = np.array([0, 0, 0])
COLOR_BLUE = np.array([0, 172, 239])
COLOR_WHITE = np.array([255, 255, 255])

TRICOLOR_TOLERANCE = 110
CLEAN_THRESHOLD = 240

def process_clean_background(img):
    # 清洗背景：亮度高于阈值的转为纯白
    return img.point(lambda p: 255 if p > CLEAN_THRESHOLD else p)

def process_tricolor(img):
    # 三值化处理：将像素分类为黑、蓝、白
    if img.mode != 'RGB':
        img = img.convert('RGB')

    data = np.array(img)
    dist_black = np.linalg.norm(data - COLOR_BLACK, axis=2)
    dist_blue = np.linalg.norm(data - COLOR_BLUE, axis=2)

    result = np.full_like(data, COLOR_WHITE)
    is_close_to_black = dist_black < TRICOLOR_TOLERANCE
    is_close_to_blue = dist_blue < TRICOLOR_TOLERANCE

    # 颜色冲突判定
    final_black_mask = is_close_to_black & (dist_black <= dist_blue)
    final_blue_mask = is_close_to_blue & (dist_blue < dist_black)

    result[final_black_mask] = COLOR_BLACK
    result[final_blue_mask] = COLOR_BLUE

    return Image.fromarray(result)

def main():
    input_path = Path(INPUT_DIR)
    out_path_clean = Path(OUTPUT_DIR_CLEAN)
    out_path_tricolor = Path(OUTPUT_DIR_TRICOLOR)

    out_path_clean.mkdir(parents=True, exist_ok=True)
    out_path_tricolor.mkdir(parents=True, exist_ok=True)

    files = sorted(input_path.glob("*.png"), key=lambda x: int(x.stem))

    for i, file_path in enumerate(files):
        try:
            page_num = int(file_path.stem)
            with Image.open(file_path) as img:
                # 区分奇偶页裁剪
                crop_box = ODD_PAGE_CROP_BOX if page_num % 2 != 0 else EVEN_PAGE_CROP_BOX
                cropped_img = img.crop(crop_box)

                process_clean_background(cropped_img.copy()).save(out_path_clean / f"{page_num}.png")
                process_tricolor(cropped_img).save(out_path_tricolor / f"{page_num}.png")

        except Exception as e:
            print(f"Error 第 {page_num} 页: {e}")

if __name__ == "__main__":
    main()