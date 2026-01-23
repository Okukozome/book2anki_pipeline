import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from pathlib import Path

# 配置参数
OUTPUT_CARDS_DIR = "final_cards"

Image.MAX_IMAGE_PIXELS = None


class VisualChecker:
    def __init__(self, root, directory):
        self.root = root
        self.directory = Path(directory)
        self.files = self.get_valid_files()
        self.current_index = 0

        self.root.title(f"快速目视检查工具 - {len(self.files)} 张待检查")
        self.root.geometry("900x750")  # 稍微加高一点窗口

        # 顶部提示
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(pady=10)
        tk.Label(self.top_frame, text="操作指南：[←/→] 翻页 | [Enter] 标记为错误 (重命名为 Unknown)",
                 font=("Arial", 10), fg="gray").pack()

        # 图片显示区域 (使用 Frame 固定大小，避免界面跳动)
        self.img_container = tk.Frame(root, width=860, height=550)
        self.img_container.pack(pady=10)
        self.img_container.pack_propagate(False)  # 禁止自动收缩

        self.img_label = tk.Label(self.img_container, text="准备加载...", bg="#f0f0f0")
        self.img_label.pack(expand=True, fill="both")

        # 当前文件名（即识别结果）显示
        self.filename_label = tk.Label(root, text="", font=("Arial", 24, "bold"), fg="#333")
        self.filename_label.pack(pady=10)

        # 进度信息
        self.status_label = tk.Label(root, text="", font=("Arial", 12))
        self.status_label.pack(pady=5)

        # 绑定键盘事件
        root.bind('<Left>', self.prev_image)
        root.bind('<Right>', self.next_image)
        root.bind('<Return>', self.mark_as_unknown)

        # 初始加载
        if not self.files:
            messagebox.showinfo("提示", "没有找到需要检查的文件 (非 Unknown 开头的文件)。")
            root.destroy()
        else:
            self.load_image()
            self.root.focus_set()

    def get_valid_files(self):
        """获取所有非 Unknown 开头的 png 文件，并按坐标排序"""
        if not self.directory.exists():
            return []

        all_files = list(self.directory.glob("*.png"))
        valid_files = []

        for f in all_files:
            if not f.name.lower().startswith("unknown"):
                valid_files.append(f)

        def sort_key(f):
            try:
                return int(f.stem.split('_')[-1])
            except (ValueError, IndexError):
                return 0

        valid_files.sort(key=sort_key)
        return valid_files

    def load_image(self):
        if not self.files:
            messagebox.showinfo("完成", "所有文件检查完毕！")
            self.root.destroy()
            return

        if self.current_index >= len(self.files):
            self.current_index = len(self.files) - 1
        if self.current_index < 0:
            self.current_index = 0

        current_file = self.files[self.current_index]

        # 显示文件名（去掉后缀坐标）
        display_name = current_file.stem.rsplit('_', 1)[0]

        self.filename_label.config(text=display_name, fg="blue")
        self.status_label.config(
            text=f"进度: {self.current_index + 1}/{len(self.files)}  (原始文件: {current_file.name})")

        try:
            pil_image = Image.open(current_file)

            # --- 修改后的缩放逻辑 ---
            # 目标显示区域大小
            display_width = 860
            display_height = 550  # 图片显示区域的最大高度

            # 1. 强制按照宽度进行等比缩放
            scale_ratio = display_width / float(pil_image.size[0])
            new_height = int(float(pil_image.size[1]) * float(scale_ratio))

            # 使用 LANCZOS 保证文字清晰度
            pil_image = pil_image.resize((display_width, new_height), Image.Resampling.LANCZOS)

            # 2. 如果高度超过显示区域，直接裁剪底部 (只保留顶部 550px)
            if new_height > display_height:
                # crop(left, top, right, bottom)
                pil_image = pil_image.crop((0, 0, display_width, display_height))
            # ---------------------

            self.tk_image = ImageTk.PhotoImage(pil_image)
            self.img_label.config(image=self.tk_image, text="")

        except Exception as e:
            self.img_label.config(image='', text=f"无法加载图片: {e}")

    def next_image(self, event=None):
        if self.current_index < len(self.files) - 1:
            self.current_index += 1
            self.load_image()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def mark_as_unknown(self, event=None):
        if not self.files:
            return

        current_file = self.files[self.current_index]

        try:
            suffix = current_file.name.split('_')[-1]
            new_filename = f"Unknown_{suffix}"
            new_path = self.directory / new_filename

            os.rename(current_file, new_path)
            print(f"已标记错误: {current_file.name} -> {new_filename}")

            del self.files[self.current_index]
            self.load_image()

        except OSError as e:
            messagebox.showerror("错误", f"重命名失败: {e}")


def main():
    root = tk.Tk()
    if not os.path.exists(OUTPUT_CARDS_DIR):
        print(f"目录 {OUTPUT_CARDS_DIR} 不存在")
        return

    app = VisualChecker(root, OUTPUT_CARDS_DIR)
    root.mainloop()


if __name__ == "__main__":
    main()