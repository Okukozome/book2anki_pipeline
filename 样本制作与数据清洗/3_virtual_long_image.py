import os
import json
from PIL import Image
from pathlib import Path

# 配置区域
CROPPED_DIR = "cropped_pages_dir"
CONFIG_FILE = "long_image.json"

# 指定正文的起始页码和结束页码（文件名中的数字）
# 去除封面、目录和封底，只保留正文
START_PAGE_INDEX = 30
END_PAGE_INDEX = 498

class VirtualLongImage:
    def __init__(self, config_path=None, create_new_from_dir=None, page_range=None):
        """
        初始化虚拟长图对象。
        :param config_path: 读取已有的 json 配置文件
        :param create_new_from_dir: 从指定目录创建新配置 (目录路径)
        :param page_range: (start, end) 元组，用于创建配置
        """
        self.pages = {}  # 缓存加载的图片对象

        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
        elif create_new_from_dir and page_range:
            self.create_config(create_new_from_dir, page_range[0], page_range[1])
        else:
            raise ValueError("必须提供 config_path 或 (create_new_from_dir, page_range)")

    def create_config(self, source_dir, start_idx, end_idx):
        """扫描目录并验证一致性，生成配置数据"""
        self.source_dir = source_dir
        self.start_index = start_idx
        self.end_index = end_idx

        # 验证第一张图以获取尺寸
        first_img_path = os.path.join(source_dir, f"{start_idx}.png")
        if not os.path.exists(first_img_path):
            raise FileNotFoundError(f"起始页不存在: {first_img_path}")

        with Image.open(first_img_path) as img:
            self.page_width, self.page_height = img.size

        # 检查所有文件是否存在
        for i in range(start_idx, end_idx + 1):
            p = os.path.join(source_dir, f"{i}.png")
            if not os.path.exists(p):
                raise FileNotFoundError(f"缺失文件: {p}")

        # 计算虚拟总高度
        self.total_pages = (end_idx - start_idx) + 1
        self.total_height = self.total_pages * self.page_height

        print(f"虚拟长图初始化成功: 宽 {self.page_width}, 总高 {self.total_height}, 页数 {self.total_pages}")

    def save_config(self, save_path):
        data = {
            "source_dir": self.source_dir,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "page_width": self.page_width,
            "page_height": self.page_height,
            "total_height": self.total_height
        }
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"配置已保存至: {save_path}")

    def load_config(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.source_dir = data["source_dir"]
        self.start_index = data["start_index"]
        self.end_index = data["end_index"]
        self.page_width = data["page_width"]
        self.page_height = data["page_height"]
        self.total_height = data["total_height"]

    def get_slice(self, y_start, y_end):
        """
        核心方法：根据全局 Y 坐标返回拼接后的图片对象
        """
        if y_start < 0 or y_end > self.total_height:
            raise ValueError(f"请求范围 {y_start}-{y_end} 超出边界 (0-{self.total_height})")

        # 1. 计算涉及的页码范围
        # 这里的 page_offset 是相对于 start_index 的偏移量 (0, 1, 2...)
        first_page_offset = int(y_start // self.page_height)
        last_page_offset = int(y_end // self.page_height)

        # 2. 收集需要的图片片段
        slices = []
        target_height = y_end - y_start

        for offset in range(first_page_offset, last_page_offset + 1):
            real_page_num = self.start_index + offset
            img_path = os.path.join(self.source_dir, f"{real_page_num}.png")

            with Image.open(img_path) as page_img:
                # 当前页在全局坐标中的起始 Y
                page_global_y_start = offset * self.page_height

                # 计算在当前页内部的裁剪区域 (local_top, local_bottom)
                # 顶部：如果是第一张涉及的图，取余数；否则从 0 开始
                local_top = (y_start - page_global_y_start) if offset == first_page_offset else 0

                # 底部：如果是最后一张涉及的图，计算剩余量；否则取完整高度
                local_bottom = (y_end - page_global_y_start) if offset == last_page_offset else self.page_height

                # 裁剪
                # crop 接受 (left, top, right, bottom)
                segment = page_img.crop((0, local_top, self.page_width, local_bottom))
                slices.append(segment.copy())  # copy是必须的，因为文件上下文会关闭

        # 3. 拼接图片
        if not slices:
            return None

        final_img = Image.new('RGB', (self.page_width, int(target_height)))
        current_y = 0
        for s in slices:
            final_img.paste(s, (0, current_y))
            current_y += s.height

        return final_img


# 主程序入口
if __name__ == "__main__":
    # 1. 初始化并保存配置
    try:
        v_img = VirtualLongImage(
            create_new_from_dir=CROPPED_DIR,
            page_range=(START_PAGE_INDEX, END_PAGE_INDEX)
        )
        v_img.save_config(CONFIG_FILE)

        # 2. 测试切片功能 (跨页测试)
        h = v_img.page_height * 100
        test_y_start = h - 300  # 第100页最后300像素
        test_y_end = h + 300  # 第101页开始300像素

        print(f"正在测试跨页切片: Y轴 {test_y_start} - {test_y_end} ...")
        slice_img = v_img.get_slice(test_y_start, test_y_end)

        slice_save_path = "test_slice.png"
        slice_img.save(slice_save_path)
        print(f"测试切片已保存为 {slice_save_path}，请检查拼接处是否自然。")

    except Exception as e:
        print(f"错误: {e}")