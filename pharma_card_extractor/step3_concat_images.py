import os
from pathlib import Path
from PIL import Image

START_PAGE_INDEX = 30
END_PAGE_INDEX = 498
DIR_CLEAN = "cropped_pages_clean"
DIR_TRICOLOR = "cropped_pages_tricolor"
OUT_FILENAME_CLEAN = "long_image_clean.png"
OUT_FILENAME_TRICOLOR = "long_image_tricolor.png"

Image.MAX_IMAGE_PIXELS = None

def get_image_files(input_dir, start_idx, end_idx):
    dir_path = Path(input_dir)
    image_files = []
    for i in range(start_idx, end_idx + 1):
        file_path = dir_path / f"{i}.png"
        if file_path.exists():
            image_files.append(file_path)
    return image_files

def create_long_image(input_dir_name, output_filename):
    files = get_image_files(input_dir_name, START_PAGE_INDEX, END_PAGE_INDEX)
    if not files: return

    try:
        # 计算总高度和最大宽度
        widths, heights = [], []
        for p in files:
            with Image.open(p) as img:
                widths.append(img.width)
                heights.append(img.height)

        max_width = max(widths)
        total_height = sum(heights)
        canvas = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))

        # 垂直拼接图像
        current_y = 0
        for file_path in files:
            with Image.open(file_path) as img:
                canvas.paste(img, (0, current_y))
                current_y += img.height

        canvas.save(output_filename, format="PNG", optimize=False)

    except Exception as e:
        print(f"错误: {e}")

def main():
    create_long_image(DIR_CLEAN, OUT_FILENAME_CLEAN)
    create_long_image(DIR_TRICOLOR, OUT_FILENAME_TRICOLOR)

if __name__ == "__main__":
    main()