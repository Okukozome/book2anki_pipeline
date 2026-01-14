import os
from pdf2image import convert_from_path
from pathlib import Path

# === 配置区域 ===
PDF_PATH = r"药理学.pdf"  # PDF文件名
OUTPUT_DIR = "raw_pages_dir"  # 输出目录
DPI = 300
CURRENT_DIR = os.getcwd()
POPPLER_PATH = os.path.join(CURRENT_DIR, "poppler-25.12.0", "Library", "bin")
print(f"Poppler path set to: {POPPLER_PATH}")

# 拆分函数
def split_pdf():
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"正在读取 PDF: {PDF_PATH} ...")

    try:
        convert_from_path(
            PDF_PATH,
            dpi=DPI,
            output_folder=OUTPUT_DIR,
            fmt='png',
            output_file='page',
            poppler_path=POPPLER_PATH,
            paths_only=True
        )

        print("PDF拆分完成，正在重命名文件...")
        files = sorted(list(output_path.glob("*.png")))
        for i, file_path in enumerate(files):
            new_name = output_path / f"{i + 1}.png"
            if new_name.exists() and new_name != file_path:
                os.remove(new_name)
            os.rename(file_path, new_name)

        print(f"处理完成！共生成 {len(files)} 张图片，保存在 {OUTPUT_DIR}")

    except Exception as e:
        print(f"发生错误: {e}")
        print("提示: Windows用户常见错误是未安装Poppler或未配置路径。")

if __name__ == "__main__":
    split_pdf()