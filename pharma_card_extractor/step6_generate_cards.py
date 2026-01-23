import os
import json
import base64
import http.client
import re
import time
import io
from pathlib import Path
from PIL import Image

# 配置参数
TITLES_DIR = "titles_preprocessed"
CLEAN_IMAGE_PATH = "long_image_clean.png"
OUTPUT_CARDS_DIR = "final_cards"

ENHANCE_THRESHOLD = 160

# API 配置
API_HOST = "api2.aigcbest.top"
API_ENDPOINT = "/v1/responses"
MODEL_NAME = "gpt-5-mini"

Image.MAX_IMAGE_PIXELS = None


def load_api_key():
    """从 .env 加载 API_KEY"""
    env_path = Path(".env")
    api_key = None

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "API_KEY":
                        api_key = value.strip()
                        break

    if not api_key:
        api_key = os.environ.get("API_KEY")

    if not api_key:
        print("错误：未找到 API_KEY。请在 .env 文件中配置。")
        exit(1)

    return api_key


def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"图片读取失败: {e}")
        return None


def call_multimodal_api(api_key, image_path):
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return None, "图片转Base64失败"

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    payload = json.dumps({
        "model": MODEL_NAME,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "请将这张图片中的药品名称提取出来。只输出识别到的文字本身，不要包含任何标点符号、解释或多余的描述。如果无法识别，请输出 Unknown。"
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{base64_image}"
                    }
                ]
            }
        ],
        "max_output_tokens": 4096
    })

    try:
        conn = http.client.HTTPSConnection(API_HOST, timeout=30)
        conn.request("POST", API_ENDPOINT, payload, headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()

        try:
            response_json = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            return None, f"JSON解析失败: {data[:100]}..."

        if res.status != 200:
            return None, f"HTTP {res.status}: {response_json}"

        # 遍历 output 列表的所有项
        if "output" in response_json and isinstance(response_json["output"], list):
            full_text = ""

            # 遍历 output 列表 (可能包含 reasoning 和 message)
            for item in response_json["output"]:
                # 只有包含 content 字段的项才包含文本 (跳过 reasoning)
                if "content" in item and isinstance(item["content"], list):
                    for content_item in item["content"]:
                        if content_item.get("type") == "output_text":
                            full_text += content_item.get("text", "")

            cleaned_text = full_text.strip()

            if not cleaned_text:
                return None, f"模型返回内容为空，原始响应: {json.dumps(response_json, ensure_ascii=False)}"

            return cleaned_text, None
        # 修改结束

        else:
            return None, f"API结构异常: {response_json}"

    except Exception as e:
        return None, f"请求异常: {str(e)}"


def sanitize_filename(text):
    if not text:
        return "Unknown"
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    text = text.replace('\n', '').replace('\r', '').strip()
    return text[:50]


def main():
    api_key = load_api_key()
    print(f"API Key 已加载，模型: {MODEL_NAME}")

    titles_path = Path(TITLES_DIR)
    if not titles_path.exists():
        print(f"错误：找不到目录 {TITLES_DIR}")
        return

    output_path = Path(OUTPUT_CARDS_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    files = list(titles_path.glob("*.png"))
    if not files:
        print("错误：目录下无图片文件")
        return

    sorted_files = []
    for f in files:
        try:
            y = int(f.stem)
            sorted_files.append((y, f))
        except ValueError:
            pass
    sorted_files.sort(key=lambda x: x[0])

    print(f"加载了 {len(sorted_files)} 个切分点")

    try:
        big_img = Image.open(CLEAN_IMAGE_PATH)
        full_width, full_height = big_img.size
    except Exception as e:
        print(f"无法加载大图: {e}")
        return

    print("开始处理...")

    for i in range(len(sorted_files)):
        current_y, title_img_path = sorted_files[i]

        crop_start_y = current_y
        if i < len(sorted_files) - 1:
            next_y = sorted_files[i + 1][0]
            crop_end_y = next_y
        else:
            crop_end_y = full_height

        print(f"[{i + 1}/{len(sorted_files)}] 识别 {title_img_path.name}... ", end="", flush=True)

        ocr_text, error_msg = call_multimodal_api(api_key, title_img_path)

        if not ocr_text:
            ocr_text = "Unknown"
            print(f"失败 -> 原因: {error_msg}")
        else:
            print(f"结果: '{ocr_text}'")

        safe_name = sanitize_filename(ocr_text)
        final_filename = f"{safe_name}_{crop_start_y}.png"
        save_path = output_path / final_filename

        try:
            crop = big_img.crop((0, crop_start_y, full_width, crop_end_y))
            crop.save(save_path)
        except Exception as e:
            print(f"保存失败: {e}")

    print(f"\n任务完成，结果目录: {OUTPUT_CARDS_DIR}")


if __name__ == "__main__":
    main()