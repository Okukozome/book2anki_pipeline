import os
import numpy as np
from PIL import Image
from pathlib import Path

# === 配置区域 ===

# 路径配置
INPUT_DIR = "raw_pages_dir"  # 输入: 原始图片目录
OUTPUT_DIR_CLEAN = "cropped_pages_clean"  # 输出1: 仅清洗背景 (适合OCR)
OUTPUT_DIR_TRICOLOR = "cropped_pages_tricolor"  # 输出2: 三值化纯色 (适合定位)

# 裁剪区域定义: (左, 上, 右, 下)
ODD_PAGE_CROP_BOX = (376, 255, 2197, 3120)  # 奇数页
EVEN_PAGE_CROP_BOX = (274, 255, 2095, 3120)  # 偶数页

# 三值化颜色定义 (RGB)
COLOR_BLACK = np.array([0, 0, 0])  # 目标黑色
COLOR_BLUE = np.array([0, 172, 239])  # 目标蓝色 (#00ACEF)
COLOR_WHITE = np.array([255, 255, 255])  # 背景白色

# 三值化容差阈值 (0 ~ 441)
# 作用：像素颜色与目标颜色的“距离”小于此值时，会被判定为目标颜色。
TRICOLOR_TOLERANCE = 110

# 背景清洗阈值 (0 ~ 255)
# 作用：在保留原色模式下，亮度大于此值的像素会被强制变为纯白。
CLEAN_THRESHOLD = 240


# 核心处理函数
def process_clean_background(img):
    """
    逻辑A：仅清洗背景。
    保留原始的抗锯齿和颜色深浅，仅将接近白色的背景(>240)变为纯白(255)。
    这种图包含了最丰富的细节，通常 OCR 效果最好。
    """
    # 使用 point 函数对每个通道进行快速处理
    # 注意：如果图片是 RGB，会对 R,G,B 分别判断。
    return img.point(lambda p: 255 if p > CLEAN_THRESHOLD else p)


def process_tricolor(img):
    """
    逻辑B：三值化 (黑/蓝/白)。
    利用 NumPy 进行向量化计算，将像素强制归类为黑、蓝或白。
    这种图对比度极高，去除了所有杂色，适合通过颜色定位标题。
    """
    # 确保图片为 RGB 模式
    if img.mode != 'RGB':
        img = img.convert('RGB')

    data = np.array(img)  # (H, W, 3)

    # 计算欧几里得距离
    dist_black = np.linalg.norm(data - COLOR_BLACK, axis=2)
    dist_blue = np.linalg.norm(data - COLOR_BLUE, axis=2)

    # 初始化全白画布
    result = np.full_like(data, COLOR_WHITE)

    # 生成掩码
    is_close_to_black = dist_black < TRICOLOR_TOLERANCE
    is_close_to_blue = dist_blue < TRICOLOR_TOLERANCE

    # 冲突处理与赋值
    # 如果离黑色更近 -> 黑
    final_black_mask = is_close_to_black & (dist_black <= dist_blue)
    # 如果离蓝色更近 -> 蓝
    final_blue_mask = is_close_to_blue & (dist_blue < dist_black)

    result[final_black_mask] = COLOR_BLACK
    result[final_blue_mask] = COLOR_BLUE

    return Image.fromarray(result)


# 主流程
def main():
    # 准备路径
    input_path = Path(INPUT_DIR)
    out_path_clean = Path(OUTPUT_DIR_CLEAN)
    out_path_tricolor = Path(OUTPUT_DIR_TRICOLOR)

    out_path_clean.mkdir(parents=True, exist_ok=True)
    out_path_tricolor.mkdir(parents=True, exist_ok=True)

    # 获取并排序文件
    files = sorted(input_path.glob("*.png"), key=lambda x: int(x.stem))

    if not files:
        print(f"错误：在 {INPUT_DIR} 中未找到图片。")
        return

    print(f"=== 裁剪和颜色处理开始 ===")
    print(f"共 {len(files)} 张图片")
    print(f"输出 A (OCR用): {OUTPUT_DIR_CLEAN}")
    print(f"输出 B (定位用): {OUTPUT_DIR_TRICOLOR}")
    print("-" * 30)

    for i, file_path in enumerate(files):
        try:
            page_num = int(file_path.stem)

            with Image.open(file_path) as img:
                # 统一裁剪
                if page_num % 2 != 0:
                    crop_box = ODD_PAGE_CROP_BOX
                else:
                    crop_box = EVEN_PAGE_CROP_BOX

                cropped_img = img.crop(crop_box)

                # 生成版本 A: 清洗背景
                # 注意：这里copy一份，避免修改原对象影响后续操作
                img_clean = process_clean_background(cropped_img.copy())
                img_clean.save(out_path_clean / f"{page_num}.png")

                # 生成版本 B: 三值化
                img_tricolor = process_tricolor(cropped_img)
                img_tricolor.save(out_path_tricolor / f"{page_num}.png")

            # 进度打印
            if (i + 1) % 50 == 0:
                print(f"进度: {i + 1}/{len(files)} 页已完成...")

        except Exception as e:
            print(f"[Error] 处理第 {page_num} 页时出错: {e}")

    print("-" * 30)
    print("全部完成！")


if __name__ == "__main__":
    main()