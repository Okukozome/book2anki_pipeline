import os
from pathlib import Path
from PIL import Image, ImageOps, ImageChops

# === 配置参数 ===
INPUT_DIR = "check_titles_dir"
OUTPUT_DIR = "titles_preprocessed"

# 噪音阈值 (0-255)
CONTENT_THRESHOLD = 240

PADDING_X = 20  # 左右膨胀
PADDING_Y = 6  # 上下膨胀

Image.MAX_IMAGE_PIXELS = None


def get_manual_bbox(img_gray, threshold):
    """
    计算内容包围盒，包含去噪逻辑：
    1. 二值化：将内容转为高亮，背景转为黑色。
    2. 边缘屏蔽：强制忽略图片四周的一圈像素（去除边缘扫描噪声）。
    3. 获取包围盒。
    """
    width, height = img_gray.size

    # === 1. 二值化处理 ===
    binary = img_gray.point(lambda p: 255 if p < threshold else 0)

    # === 2. 边缘屏蔽 (去除边缘噪点) ===
    edge_margin = 15  # 忽略边缘多少像素的噪点

    if width <= 2 * edge_margin or height <= 2 * edge_margin:
        # 如果图片太小，就不做边缘屏蔽了，直接从二值图取
        bbox = binary.getbbox()
    else:
        # 创建一个纯黑的底图
        clean_binary = Image.new("L", (width, height), 0)

        # 将原二值图的“中心部分”扣出来，贴到纯黑底图上
        box = (edge_margin, edge_margin, width - edge_margin, height - edge_margin)
        crop = binary.crop(box)
        clean_binary.paste(crop, box)

        # 使用处理过边缘的图来计算 bbox
        bbox = clean_binary.getbbox()

    return bbox


def process_single_image(img_path, output_dir):
    try:
        with Image.open(img_path) as img:
            # 转换为灰度图 (保留抗锯齿边缘，不做二值化)
            gray = img.convert("L")

            # 手动计算裁剪框
            bbox = get_manual_bbox(gray, CONTENT_THRESHOLD)

            if not bbox:
                print(f"  [跳过] {img_path.name}: 未检测到有效内容 (看似全白)")
                return

            left, top, right, bottom = bbox
            width, height = gray.size

            # 计算膨胀后的坐标
            new_left = max(0, left - PADDING_X)
            new_top = max(0, top - PADDING_Y)
            new_right = min(width, right + PADDING_X)
            new_bottom = min(height, bottom + PADDING_Y)

            # 裁剪 (裁剪的是灰度原图)
            cropped_img = gray.crop((new_left, new_top, new_right, new_bottom))
            cropped_img = ImageOps.autocontrast(cropped_img, cutoff=0)

            # 保存
            save_path = output_dir / img_path.name
            cropped_img.save(save_path)

    except Exception as e:
        print(f"  [错误] 处理 {img_path.name} 失败: {e}")


def main():
    input_path = Path(INPUT_DIR)
    output_path = Path(OUTPUT_DIR)

    if not input_path.exists():
        print(f"错误：找不到输入目录 {INPUT_DIR}")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    files = list(input_path.glob("*.png"))
    # 按数字排序
    files.sort(key=lambda f: int(f.stem) if f.stem.isdigit() else 0)

    print(f"开始处理: {INPUT_DIR} -> {OUTPUT_DIR}")
    print(f"模式: 保留灰度 + 手动去噪裁剪")
    print(f"内容识别阈值: < {CONTENT_THRESHOLD} ")
    print("-" * 30)

    count = 0
    for f in files:
        process_single_image(f, output_path)
        count += 1
        if count % 10 == 0:
            print(f"已处理 {count}/{len(files)}...")

    print("-" * 30)
    print(f"处理完成！\n请检查 '{OUTPUT_DIR}'。")


if __name__ == "__main__":
    main()