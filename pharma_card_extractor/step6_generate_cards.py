import os
import json
import base64
import http.client
import re
from pathlib import Path
from PIL import Image

TITLES_DIR = "titles_preprocessed"
CLEAN_IMAGE_PATH = "long_image_clean.png"
OUTPUT_CARDS_DIR = "final_cards"
API_HOST = "api2.aigcbest.top"
API_ENDPOINT = "/v1/responses"
MODEL_NAME = "gpt-5-mini"

Image.MAX_IMAGE_PIXELS = None


def load_api_key():
    # 获取API密钥
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    if key.strip() == "API_KEY": return value.strip()
    return os.environ.get("API_KEY")


def call_multimodal_api(api_key, image_path):
    # 调用多模态API识别药品名称
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')

    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = json.dumps({
        "model": MODEL_NAME,
        "input": [{"role": "user", "content": [
            {"type": "input_text", "text": "提取图片中的药品名称，只输出文字。"},
            {"type": "input_image", "image_url": f"data:image/png;base64,{base64_image}"}
        ]}],
        "max_output_tokens": 4096
    })

    conn = http.client.HTTPSConnection(API_HOST, timeout=30)
    conn.request("POST", API_ENDPOINT, payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()

    response_json = json.loads(data)
    if res.status == 200:
        full_text = ""
        for item in response_json.get("output", []):
            if "content" in item:
                for content_item in item["content"]:
                    if content_item.get("type") == "output_text":
                        full_text += content_item.get("text", "")
        return full_text.strip(), None
    return None, f"Error {res.status}"


def sanitize_filename(text):
    if not text: return "Unknown"
    text = re.sub(r'[\\/:*?"<>|]', '_', text)
    return text.replace('\n', '').replace('\r', '').strip()[:50]


def main():
    api_key = load_api_key()
    titles_path = Path(TITLES_DIR)
    output_path = Path(OUTPUT_CARDS_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    files = sorted([(int(f.stem), f) for f in titles_path.glob("*.png") if f.stem.isdigit()], key=lambda x: x[0])
    big_img = Image.open(CLEAN_IMAGE_PATH)

    for i, (current_y, title_img_path) in enumerate(files):
        crop_end_y = files[i + 1][0] if i < len(files) - 1 else big_img.height
        ocr_text, _ = call_multimodal_api(api_key, title_img_path)

        safe_name = sanitize_filename(ocr_text or "Unknown")
        big_img.crop((0, current_y, big_img.width, crop_end_y)).save(output_path / f"{safe_name}_{current_y}.png")


if __name__ == "__main__":
    main()