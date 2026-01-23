import os
from pdf2image import convert_from_path
from pathlib import Path

PDF_PATH = r"药理学.pdf"
OUTPUT_DIR = "raw_pages_dir"
DPI = 300
CURRENT_DIR = os.getcwd()
POPPLER_PATH = os.path.join(CURRENT_DIR, "poppler-25.12.0", "Library", "bin")

def split_pdf():
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # 将PDF页面转换为PNG图像
        convert_from_path(
            PDF_PATH,
            dpi=DPI,
            output_folder=OUTPUT_DIR,
            fmt='png',
            output_file='page',
            poppler_path=POPPLER_PATH,
            paths_only=True
        )

        # 统一重命名为数字序列
        files = sorted(list(output_path.glob("*.png")))
        for i, file_path in enumerate(files):
            new_name = output_path / f"{i + 1}.png"
            if new_name.exists() and new_name != file_path:
                os.remove(new_name)
            os.rename(file_path, new_name)

    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    split_pdf()