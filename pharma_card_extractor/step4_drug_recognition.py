import os
import numpy as np
from PIL import Image
from pathlib import Path
import gc

TRICOLOR_IMAGE_PATH = "long_image_tricolor.png"
CLEAN_IMAGE_PATH = "long_image_clean.png"
OUTPUT_CHECK_DIR = "check_titles_dir"

COLOR_BLUE = np.array([0, 172, 239])
COLOR_WHITE = np.array([255, 255, 255])

# 垂直形态特征
MIN_TOP_WHITE_H = 10
MIN_BLUE_REGION_H = 38
MAX_BLUE_REGION_H = 58
MIN_BOTTOM_WHITE_H = 39

# 水平形态特征
MIN_WIDTH_THRESHOLD = 44
MAX_CONT_BLUE_PIXELS = 66
EDGE_MARGIN = 150
CENTER_LEFT_LIMIT = 900
CENTER_RIGHT_LIMIT = 901

Image.MAX_IMAGE_PIXELS = None


def calculate_max_continuous(bool_arr):
    # 计算最长连续True序列长度
    if not np.any(bool_arr): return 0
    padded = np.concatenate(([False], bool_arr, [False]))
    diff = np.diff(padded.astype(int))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    return (ends - starts).max() if len(starts) > 0 else 0


def step1_analyze_structure(image_array):
    # 分析行特征：0为纯白，1为含蓝，2为含杂色
    is_white = np.all(image_array == COLOR_WHITE, axis=2)
    is_blue = np.all(image_array == COLOR_BLUE, axis=2)
    row_has_other = np.any(~(is_white | is_blue), axis=1)
    row_has_blue = np.any(is_blue, axis=1)

    row_status = np.zeros(image_array.shape[0], dtype=np.int8)
    row_status[row_has_other] = 2
    row_status[row_has_blue & ~row_has_other] = 1
    return row_status, is_blue, image_array.shape[1]


def step2_find_candidates(row_status, is_blue_matrix, img_width):
    # 扫描符合标题波形特征的区域
    candidates = []
    h = len(row_status)
    edge_right_limit = img_width - EDGE_MARGIN
    i = 0
    while i < h:
        if row_status[i] != 1:
            i += 1
            continue

        # 检查上方留白高度
        top_white_count = 0
        p = i - 1
        while p >= 0 and row_status[p] == 0:
            top_white_count += 1
            p -= 1
        if top_white_count <= MIN_TOP_WHITE_H:
            while i < h and row_status[i] == 1: i += 1
            continue

        # 检查蓝色区域高度
        blue_start = i
        while i < h and row_status[i] == 1: i += 1
        blue_end = i
        blue_height = blue_end - blue_start
        if not (MIN_BLUE_REGION_H <= blue_height <= MAX_BLUE_REGION_H): continue

        # 检查下方留白高度
        bottom_white_count = 0
        p = i
        while p < h and row_status[p] == 0:
            bottom_white_count += 1
            p += 1
        if bottom_white_count <= MIN_BOTTOM_WHITE_H: continue

        # 像素级校验：排除长横条、检查宽度及边缘距离
        valid_candidate = True
        all_min_x, all_max_x = [], []
        max_width_diff = 0
        for r in range(blue_start, blue_end):
            row_bool = is_blue_matrix[r]
            indices = np.where(row_bool)[0]
            if len(indices) == 0: continue
            x_l, x_r = indices[0], indices[-1]
            all_min_x.append(x_l)
            all_max_x.append(x_r)
            max_width_diff = max(max_width_diff, x_r - x_l)
            if calculate_max_continuous(row_bool) >= MAX_CONT_BLUE_PIXELS:
                valid_candidate = False;
                break

        if not valid_candidate or not all_min_x or max_width_diff <= MIN_WIDTH_THRESHOLD: continue

        block_min_x, block_max_x = min(all_min_x), max(all_max_x)
        if block_min_x <= EDGE_MARGIN or block_max_x >= edge_right_limit: continue
        if block_max_x <= CENTER_LEFT_LIMIT or block_min_x >= CENTER_RIGHT_LIMIT: continue

        candidates.append((blue_start - top_white_count, blue_end + bottom_white_count))
    return candidates


def step3_crop_and_save(candidates):
    # 根据识别到的坐标从原图裁剪
    if not candidates: return
    try:
        img = Image.open(CLEAN_IMAGE_PATH)
        img.load()
        out_path = Path(OUTPUT_CHECK_DIR)
        out_path.mkdir(parents=True, exist_ok=True)
        for start_y, end_y in candidates:
            img.crop((0, start_y, img.width, end_y)).save(out_path / f"{start_y}.png")
    except Exception as e:
        print(f"裁剪出错: {e}")


def main():
    if not os.path.exists(TRICOLOR_IMAGE_PATH): return
    with Image.open(TRICOLOR_IMAGE_PATH) as img:
        tricolor_arr = np.array(img.convert('RGB'))

    row_status, is_blue_matrix, width = step1_analyze_structure(tricolor_arr)
    candidates = step2_find_candidates(row_status, is_blue_matrix, width)

    del tricolor_arr, row_status, is_blue_matrix
    gc.collect()
    step3_crop_and_save(candidates)


if __name__ == "__main__":
    main()