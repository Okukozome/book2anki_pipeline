import os
import re
import asyncio
import io
# === 引入 Windows SDK 库 ===
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.graphics.imaging import BitmapDecoder
from winsdk.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
# ==========================
import numpy as np
from PIL import Image
from pathlib import Path

# === 配置参数 ===
# 标题小图的目录
TITLES_DIR = "check_titles_dir"
# 原始高清长图
CLEAN_IMAGE_PATH = "long_image_clean.png"
# 最终卡片输出目录
OUTPUT_CARDS_DIR = "final_cards"

# 图像增强阈值
ENHANCE_THRESHOLD = 160

# 解除 PIL 限制
Image.MAX_IMAGE_PIXELS = None


def get_enhanced_pil_image(image_path):
    """
    读取图片并应用增强逻辑。
    修改：直接返回 PIL Image 对象，而不是 numpy 数组，方便后续转流。
    """
    try:
        img = Image.open(image_path).convert('L')
        # 增强逻辑: 小于阈值(较暗/蓝色)置为0(黑)，否则保持原样(白/浅灰)
        # 注意：Windows OCR 对白底黑字或黑底白字都很敏感，二值化有助于去除噪点
        img_enhanced = img.point(lambda x: 0 if x < ENHANCE_THRESHOLD else 255)
        # 转回 RGB 模式 (虽然是黑白)，因为 BitmapDecoder 对某些单通道处理较麻烦
        return img_enhanced.convert("RGB")
    except Exception as e:
        print(f"图像增强失败 {image_path}: {e}")
        return None


async def recognize_pil_image(ocr_engine, pil_img):
    """
    核心辅助函数：将 PIL 图片转为 Windows SoftwareBitmap 并识别
    """
    if pil_img is None:
        return ""

    try:
        # 1. 将 PIL 图片保存到内存中的 BytesIO
        output_io = io.BytesIO()
        pil_img.save(output_io, format='PNG')
        image_bytes = output_io.getvalue()

        # 2. 创建 Windows 内存流 (InMemoryRandomAccessStream)
        stream = InMemoryRandomAccessStream()
        writer = DataWriter(stream.get_output_stream_at(0))
        writer.write_bytes(list(image_bytes))
        await writer.store_async()
        await writer.flush_async()
        writer.detach_stream()  # 分离，防止关闭 writer 时关闭流

        # 3. 解码为 SoftwareBitmap
        decoder = await BitmapDecoder.create_async(stream)
        software_bitmap = await decoder.get_software_bitmap_async()

        # 4. 调用 Windows OCR 引擎
        result = await ocr_engine.recognize_async(software_bitmap)

        # 5. 拼接结果
        # Windows OCR 结果包含 lines (行) 和 words (词)
        # 直接拼接所有行的文本
        full_text = "".join([line.text for line in result.lines])
        return full_text

    except Exception as e:
        print(f"Windows OCR 内部转换/识别错误: {e}")
        return ""


def sanitize_filename(text):
    """清理文件名中的非法字符 (Windows/Linux)"""
    # 替换 / \ : * ? " < > | 为下划线
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    # 移除换行符和首尾空格
    text = text.replace('\n', '').replace('\r', '').strip()
    return text


async def main():
    # 1. 准备目录
    titles_path = Path(TITLES_DIR)
    if not titles_path.exists():
        print(f"错误：找不到标题目录 {TITLES_DIR}")
        return

    output_path = Path(OUTPUT_CARDS_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # 2. 获取并排序切分点
    files = list(titles_path.glob("*.png"))
    if not files:
        print("没有找到标题图片，请检查 check_titles_dir")
        return

    sorted_files = []
    for f in files:
        try:
            y = int(f.stem)
            sorted_files.append((y, f))
        except ValueError:
            print(f"跳过非数字命名文件: {f.name}")

    sorted_files.sort(key=lambda x: x[0])
    print(f"共加载 {len(sorted_files)} 个切分点。")

    # 3. 初始化 Windows OCR 引擎
    print("正在初始化 Windows OCR Engine...")
    # 尝试使用用户配置文件的语言（通常跟随系统语言）
    ocr_engine = OcrEngine.try_create_from_user_profile_languages()

    # 如果你想强制指定中文，可以尝试如下方式（需要系统已安装中文包）：
    # from winsdk.windows.globalization import Language
    # ocr_engine = OcrEngine.try_create_from_language(Language("zh-Hans-CN"))

    if not ocr_engine:
        print("致命错误：无法创建 OCR 引擎。请确保 Windows 设置中已安装对应语言包（如中文/英文）。")
        return
    else:
        print(f"OCR 引擎加载成功，当前识别语言: {ocr_engine.recognizer_language.display_name}")

    # 4. 加载大图
    print(f"正在加载原图: {CLEAN_IMAGE_PATH} ...")
    try:
        big_img = Image.open(CLEAN_IMAGE_PATH)
        big_img.load()
        full_width, full_height = big_img.size
    except Exception as e:
        print(f"无法加载大图: {e}")
        return

    # 5. 循环处理
    print("开始识别并生成卡片 (Windows Native OCR)...")

    for i in range(len(sorted_files)):
        current_y, title_img_path = sorted_files[i]

        # === A. 确定切分范围 ===
        crop_start_y = current_y
        if i < len(sorted_files) - 1:
            next_y = sorted_files[i + 1][0]
            crop_end_y = next_y
        else:
            crop_end_y = full_height

        # === B. 识别标题 (Windows OCR) ===
        # 获取 PIL Image 对象 (已增强)
        pil_img = get_enhanced_pil_image(title_img_path)

        ocr_text = "Unknown"
        if pil_img:
            # 异步调用识别函数
            res_text = await recognize_pil_image(ocr_engine, pil_img)
            if res_text and res_text.strip():
                ocr_text = res_text
            else:
                # 偶尔可能因为增强过度导致无法识别，可以尝试由 Windows 原生处理
                # 如果你想做回退机制，可以在这里再次读取原图尝试
                pass

        # === C. 生成文件名 ===
        safe_name = sanitize_filename(ocr_text)
        # 避免空文件名
        if not safe_name:
            safe_name = "Unknown_Text"

        final_filename = f"{safe_name}_{crop_start_y}.png"
        save_path = output_path / final_filename

        # === D. 裁剪大图并保存 ===
        try:
            crop = big_img.crop((0, crop_start_y, full_width, crop_end_y))
            crop.save(save_path)
            # 在控制台打印识别出的文字，方便你感受效果
            print(f"[{i + 1}/{len(sorted_files)}] 识别结果: '{ocr_text}' -> 保存: {final_filename}")
        except Exception as e:
            print(f"保存图片失败 {final_filename}: {e}")

    print(f"\n全部完成！结果已保存在: {OUTPUT_CARDS_DIR}")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())