import os
from pathlib import Path
from PIL import Image

# 配置区域
# 起止页码 (根据 long_image.json 的提示)
START_PAGE_INDEX = 30
END_PAGE_INDEX = 498

# 输入目录
DIR_CLEAN = "cropped_pages_clean"
DIR_TRICOLOR = "cropped_pages_tricolor"

# 输出文件名
OUT_FILENAME_CLEAN = "long_image_clean.png"
OUT_FILENAME_TRICOLOR = "long_image_tricolor.png"

# 解除 PIL 的像素限制，防止处理大图时报错，注意最好有16GB+内存
Image.MAX_IMAGE_PIXELS = None


def get_image_files(input_dir, start_idx, end_idx):
    """
    获取指定范围内存在的图片文件路径列表
    """
    dir_path = Path(input_dir)
    if not dir_path.exists():
        print(f"错误: 目录 {input_dir} 不存在")
        return []

    image_files = []
    # 遍历范围，按顺序查找图片
    for i in range(start_idx, end_idx + 1):
        file_path = dir_path / f"{i}.png"
        if file_path.exists():
            image_files.append(file_path)
        else:
            print(f"警告: 缺失图片 {file_path}")

    return image_files


def create_long_image(input_dir_name, output_filename):
    print(f"=== 正在处理: {input_dir_name} -> {output_filename} ===")

    # 获取文件列表
    files = get_image_files(input_dir_name, START_PAGE_INDEX, END_PAGE_INDEX)
    if not files:
        print("未找到任何图片，跳过。")
        return

    try:
        # 1. 预读取所有图片信息以计算总高度
        # 为了节省内存，这里暂时只读取尺寸，不加载像素
        widths = []
        heights = []
        for p in files:
            with Image.open(p) as img:
                widths.append(img.width)
                heights.append(img.height)

        # 确定画布尺寸
        max_width = max(widths)
        total_height = sum(heights)

        print(f"共 {len(files)} 张图片")
        print(f"目标画布尺寸: {max_width} x {total_height}")

        # 2. 创建画布 (RGB模式)
        # 注意：对于极大的图像，这里会分配大量内存
        canvas = Image.new('RGB', (max_width, total_height), color=(255, 255, 255))

        # 3. 逐张粘贴
        current_y = 0
        for i, file_path in enumerate(files):
            with Image.open(file_path) as img:
                # 由于已经裁剪，尺寸是相同的
                canvas.paste(img, (0, current_y))
                current_y += img.height

            # 简单的进度显示
            if (i + 1) % 50 == 0:
                print(f"已合并 {i + 1}/{len(files)} 张...")

        # 4. 保存文件
        print("正在保存长图，这可能需要一些时间...")
        output_path = Path(output_filename)

        canvas.save(output_path, format="PNG", optimize=False)

        print(f"保存成功: {output_path.absolute()}")
        print("-" * 30)

    except Exception as e:
        print(f"发生错误: {e}")


def main():
    # 执行合并 - Clean 版本
    create_long_image(DIR_CLEAN, OUT_FILENAME_CLEAN)

    # 执行合并 - Tricolor 版本
    create_long_image(DIR_TRICOLOR, OUT_FILENAME_TRICOLOR)

    print("所有任务完成。")


if __name__ == "__main__":
    main()