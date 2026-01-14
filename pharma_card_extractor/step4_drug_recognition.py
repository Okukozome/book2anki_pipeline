import os
import numpy as np
from PIL import Image
from pathlib import Path
import gc

# === 配置参数 ===
TRICOLOR_IMAGE_PATH = "long_image_tricolor.png"
CLEAN_IMAGE_PATH = "long_image_clean.png"
OUTPUT_CHECK_DIR = "check_titles_dir"

# 颜色定义 (RGB)
COLOR_BLUE = np.array([0, 172, 239])
COLOR_WHITE = np.array([255, 255, 255])

# Y轴特征阈值 (高度)
MIN_TOP_WHITE_H = 10  # 上方纯白最小高度
MIN_BLUE_REGION_H = 38  # 蓝色区域最小高度
MAX_BLUE_REGION_H = 58  # 蓝色区域最大高度
MIN_BOTTOM_WHITE_H = 39  # 下方纯白最小高度

# X轴特征阈值 (宽度与形态)
MIN_WIDTH_THRESHOLD = 44  # 至少有一行的宽度差(x_r - x_l)需大于此值
MAX_CONT_BLUE_PIXELS = 66  # 单行最大连续蓝色像素不能超过此值 (排除长横条)

# 边缘排除阈值 (像素)
EDGE_MARGIN = 150  # 左右边缘 150px 禁区

# 中轴线排除阈值
CENTER_LEFT_LIMIT = 900  # 若所有内容都在此线左侧则排除
CENTER_RIGHT_LIMIT = 901  # 若所有内容都在此线右侧则排除

# 解除 PIL 像素限制
Image.MAX_IMAGE_PIXELS = None


def calculate_max_continuous(bool_arr):
    """计算布尔数组中最长的连续 True 序列长度"""
    if not np.any(bool_arr):
        return 0
    padded = np.concatenate(([False], bool_arr, [False]))
    diff = np.diff(padded.astype(int))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    if len(starts) == 0:
        return 0
    return (ends - starts).max()


def step1_analyze_structure(image_array):
    """
    生成行级统计摘要
    Status 定义: 0=纯白, 1=含蓝且无杂色, 2=含杂色(优先级最高)
    """
    height, width, _ = image_array.shape
    print(f"正在分析矩阵结构 ({width}x{height})...")

    is_white = np.all(image_array == COLOR_WHITE, axis=2)
    is_blue = np.all(image_array == COLOR_BLUE, axis=2)

    # 只要有非白非蓝，即视为杂色(2)，优先级高于蓝色(1)
    row_has_other = np.any(~(is_white | is_blue), axis=1)
    row_has_blue = np.any(is_blue, axis=1)

    row_status = np.zeros(height, dtype=np.int8)
    row_status[row_has_other] = 2
    row_status[row_has_blue & ~row_has_other] = 1

    return row_status, is_blue, width


def step2_find_candidates(row_status, is_blue_matrix, img_width):
    """
    匹配波形模式并执行精细校验
    """
    print("正在扫描波形模式...")
    candidates = []
    h = len(row_status)
    edge_right_limit = img_width - EDGE_MARGIN

    i = 0
    while i < h:
        # 1. 寻找蓝色区域起点 (Status 1)
        if row_status[i] != 1:
            i += 1
            continue

        # 2. 回溯检查上方留白 (Status 0)
        top_white_count = 0
        p = i - 1
        while p >= 0 and row_status[p] == 0:
            top_white_count += 1
            p -= 1

        if top_white_count <= MIN_TOP_WHITE_H:
            # 上方留白不足，跳过当前蓝色块
            while i < h and row_status[i] == 1: i += 1
            continue

        # 3. 确定蓝色区域高度
        blue_start = i
        while i < h and row_status[i] == 1:
            i += 1
        blue_end = i
        blue_height = blue_end - blue_start

        if not (MIN_BLUE_REGION_H <= blue_height <= MAX_BLUE_REGION_H):
            continue

        # 4. 检查下方留白
        bottom_white_count = 0
        p = i
        while p < h and row_status[p] == 0:
            bottom_white_count += 1
            p += 1

        if bottom_white_count <= MIN_BOTTOM_WHITE_H:
            continue

        # === 像素级内容校验 ===
        valid_candidate = True
        max_width_diff = 0
        all_min_x = []
        all_max_x = []

        for r in range(blue_start, blue_end):
            row_bool = is_blue_matrix[r]
            indices = np.where(row_bool)[0]

            if len(indices) == 0: continue

            x_l = indices[0]
            x_r = indices[-1]

            all_min_x.append(x_l)
            all_max_x.append(x_r)

            # 记录最大宽度差
            width_diff = x_r - x_l
            if width_diff > max_width_diff:
                max_width_diff = width_diff

            # 排除条件：单行连续蓝色过长
            if calculate_max_continuous(row_bool) >= MAX_CONT_BLUE_PIXELS:
                valid_candidate = False
                break

        if not valid_candidate or not all_min_x:
            continue

        # 排除条件：宽度不足
        if max_width_diff <= MIN_WIDTH_THRESHOLD:
            continue

        block_min_x = min(all_min_x)
        block_max_x = max(all_max_x)

        # 排除条件：触及边缘 (左右 150px)
        # 只要有一部分进入禁区即排除
        if block_min_x <= EDGE_MARGIN or block_max_x >= edge_right_limit:
            continue

        # 排除条件：偏离中轴线
        # 全在左侧
        if block_max_x <= CENTER_LEFT_LIMIT:
            continue
        # 全在右侧
        if block_min_x >= CENTER_RIGHT_LIMIT:
            continue

        # === 记录结果 ===
        crop_start_y = blue_start - top_white_count
        crop_end_y = blue_end + bottom_white_count
        candidates.append((crop_start_y, crop_end_y))

    print(f"共发现 {len(candidates)} 个潜在药物标题。")
    return candidates


def step3_crop_and_save(candidates):
    """
    从 Clean 原图中裁剪结果
    """
    if not candidates:
        return

    print(f"正在读取 Clean 原图: {CLEAN_IMAGE_PATH} ...")
    try:
        img = Image.open(CLEAN_IMAGE_PATH)
        img.load()
        width = img.width

        out_path = Path(OUTPUT_CHECK_DIR)
        out_path.mkdir(parents=True, exist_ok=True)

        print(f"开始裁剪并保存 {len(candidates)} 张图片...")
        for start_y, end_y in candidates:
            # 裁剪区域: (left, top, right, bottom)
            crop = img.crop((0, start_y, width, end_y))
            save_name = out_path / f"{start_y}.png"
            crop.save(save_name)

        print(f"处理完成，结果已保存至 {OUTPUT_CHECK_DIR}")

    except Exception as e:
        print(f"裁剪阶段出错: {e}")


def main():
    if not os.path.exists(TRICOLOR_IMAGE_PATH):
        print("错误：找不到 tricolor 图片。")
        return

    # 1. 加载大图
    print(f"正在加载 Tricolor 图片到内存: {TRICOLOR_IMAGE_PATH} ...")
    with Image.open(TRICOLOR_IMAGE_PATH) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        tricolor_arr = np.array(img)

    # 2. 分析结构
    row_status, is_blue_matrix, width = step1_analyze_structure(tricolor_arr)

    # 3. 识别候选
    candidates = step2_find_candidates(row_status, is_blue_matrix, width)

    # 4. 释放内存
    print("释放 Tricolor 矩阵内存...")
    del tricolor_arr
    del row_status
    del is_blue_matrix
    gc.collect()

    # 5. 裁剪输出
    step3_crop_and_save(candidates)


if __name__ == "__main__":
    main()