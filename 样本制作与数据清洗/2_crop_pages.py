import os
from PIL import Image
from pathlib import Path

# 配置区域
INPUT_DIR = "raw_pages_dir"
OUTPUT_DIR = "cropped_pages_dir"

# 裁剪框定义: (左, 上, 右, 下) 坐标
# 奇数页
ODD_PAGE_CROP_BOX = (376, 252, 2197, 3120)
# 偶数页
EVEN_PAGE_CROP_BOX = (274, 252, 2095, 3120)

def crop_pages():
    input_path = Path(INPUT_DIR)
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # 获取所有数字命名的png文件并按数字顺序排序
    files = sorted(input_path.glob("*.png"), key=lambda x: int(x.stem))

    if not files:
        print("未找到源图片，请先运行步骤1。")
        return

    print(f"开始裁剪，共 {len(files)} 张图片...")

    for file_path in files:
        try:
            page_num = int(file_path.stem)

            with Image.open(file_path) as img:
                # 判断奇偶页
                if page_num % 2 != 0:  # 奇数页 (1, 3, 5...)
                    box = ODD_PAGE_CROP_BOX
                else:  # 偶数页 (2, 4, 6...)
                    box = EVEN_PAGE_CROP_BOX

                # 执行裁剪
                cropped_img = img.crop(box)

                # 二值化白色
                cropped_img = cropped_img.point(lambda p: 255 if p > 240 else p)

                # 保存到新目录
                save_path = output_path / f"{page_num}.png"

                # 保存
                cropped_img.save(save_path)

            if page_num % 50 == 0:
                print(f"已处理至第 {page_num} 页...")

        except Exception as e:
            print(f"处理第 {page_num} 页时出错: {e}")

    print(f"裁剪完成！结果保存在 {OUTPUT_DIR}")


if __name__ == "__main__":
    crop_pages()