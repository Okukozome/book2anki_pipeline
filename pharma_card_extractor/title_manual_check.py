import os
import time
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path

# === 配置 ===
IMAGE_DIR = "check_titles_dir"  # 标题裁剪的图片目录
FPS_LIMIT = 5  # 限制帧率
FRAME_INTERVAL = 1.0 / FPS_LIMIT


class DrugTitleViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("药物标题快速检查工具")
        self.root.geometry("800x400")  # 初始窗口大小

        # 1. 加载文件列表
        self.image_files = self.load_file_list()
        if not self.image_files:
            print(f"错误：在 {IMAGE_DIR} 中没有找到 png 图片。")
            root.destroy()
            return

        self.total_count = len(self.image_files)
        self.current_index = 0
        self.last_action_time = 0

        # 2. UI布局
        # 顶部信息栏
        self.info_label = tk.Label(root, text="", font=("Arial", 12, "bold"), bg="#f0f0f0")
        self.info_label.pack(side="top", fill="x", ipady=5)

        # 图片显示区域 (使用Label容器)
        self.img_label = tk.Label(root, bg="#333333")
        self.img_label.pack(expand=True, fill="both")

        # 3. 绑定按键
        # Windows 的长按会自动触发连续的 KeyPress 事件
        root.bind("<Left>", self.prev_image)
        root.bind("<Right>", self.next_image)
        root.bind("<Up>", self.prev_image)
        root.bind("<Down>", self.next_image)

        # 4. 显示第一张
        self.show_current()

        # 聚焦窗口确保按键生效
        root.focus_force()

    def load_file_list(self):
        """加载并按数字(y坐标)排序文件"""
        p = Path(IMAGE_DIR)
        if not p.exists():
            return []

        files = list(p.glob("*.png"))
        # 按文件名中的数字排序，而不是字符串排序
        try:
            files.sort(key=lambda x: int(x.stem))
        except ValueError:
            files.sort()  # 回退到字母排序

        return files

    def show_current(self):
        """核心显示逻辑"""
        fpath = self.image_files[self.current_index]

        # 更新标题栏
        self.root.title(f"查看器 - {self.current_index + 1}/{self.total_count} - {fpath.name}")
        self.info_label.config(text=f"索引: {self.current_index + 1} / {self.total_count}   |   坐标(Y): {fpath.stem}")

        # 加载图片
        try:
            # 使用 PIL 加载
            pil_img = Image.open(fpath)

            # 转换为 Tkinter 对象
            tk_img = ImageTk.PhotoImage(pil_img)

            # 更新 Label
            self.img_label.config(image=tk_img)
            self.img_label.image = tk_img

        except Exception as e:
            print(f"无法加载图片 {fpath}: {e}")

    def check_throttle(self):
        """检查是否过快 (限制 FPS)"""
        now = time.time()
        if now - self.last_action_time < FRAME_INTERVAL:
            return False
        self.last_action_time = now
        return True

    def next_image(self, event=None):
        if not self.check_throttle():
            return

        if self.current_index < self.total_count - 1:
            self.current_index += 1
            self.show_current()

    def prev_image(self, event=None):
        if not self.check_throttle():
            return

        if self.current_index > 0:
            self.current_index -= 1
            self.show_current()


if __name__ == "__main__":
    root = tk.Tk()
    app = DrugTitleViewer(root)
    root.mainloop()