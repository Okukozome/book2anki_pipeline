import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import re
from pathlib import Path

# 配置参数
OUTPUT_CARDS_DIR = "final_cards"

Image.MAX_IMAGE_PIXELS = None


class ManualRenamer:
    def __init__(self, root, directory):
        self.root = root
        self.directory = Path(directory)
        self.files = self.get_unknown_files()
        self.current_index = 0
        self.total_files = len(self.files)

        self.root.title(f"人工修复工具 - {directory}")
        self.root.geometry("800x750")

        self.img_container = tk.Frame(root, width=780, height=500)
        self.img_container.pack(pady=10)
        self.img_container.pack_propagate(False)

        self.img_label = tk.Label(self.img_container, text="图片加载区域", bg="#f0f0f0")
        self.img_label.pack(expand=True, fill="both")

        self.info_label = tk.Label(root, text="准备就绪", font=("Arial", 12))
        self.info_label.pack(pady=5)

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(root, textvariable=self.input_var, font=("Arial", 14), width=40)
        self.entry.pack(pady=10)
        self.entry.bind("<Return>", self.on_rename)  # 绑定回车键
        self.entry.focus_set()

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="重命名 (Enter)", command=self.on_rename, bg="#4CAF50", fg="white").pack(side="left",
                                                                                                           padx=10)
        tk.Button(btn_frame, text="跳过", command=self.on_skip).pack(side="left", padx=10)

        if self.total_files == 0:
            messagebox.showinfo("完成", "没有找到需要修复的 Unknown 文件！")
            root.destroy()
        else:
            self.load_image()

    def get_unknown_files(self):
        """获取所有以 Unknown 开头的 png 文件，并按坐标排序"""
        if not self.directory.exists():
            return []

        files = list(self.directory.glob("Unknown_*.png"))

        def sort_key(f):
            try:
                return int(f.stem.split('_')[-1])
            except (ValueError, IndexError):
                return 0

        files.sort(key=sort_key)
        return files

    def load_image(self):
        if self.current_index >= self.total_files:
            messagebox.showinfo("完成", "所有文件处理完毕！")
            self.root.destroy()
            return

        current_file = self.files[self.current_index]
        self.info_label.config(text=f"进度: {self.current_index + 1}/{self.total_files} | 文件: {current_file.name}")

        try:
            pil_image = Image.open(current_file)

            display_width = 780
            display_height = 500  # 最大显示高度

            # 1. 按照宽度等比缩放
            scale_ratio = display_width / float(pil_image.size[0])
            new_height = int(float(pil_image.size[1]) * float(scale_ratio))

            pil_image = pil_image.resize((display_width, new_height), Image.Resampling.LANCZOS)

            # 2. 如果缩放后的高度超过显示区，则裁剪底部，保留开头
            if new_height > display_height:
                pil_image = pil_image.crop((0, 0, display_width, display_height))

            self.tk_image = ImageTk.PhotoImage(pil_image)
            self.img_label.config(image=self.tk_image, text="")
        except Exception as e:
            self.img_label.config(image='', text=f"无法加载图片: {e}")

        # 清空输入框并聚焦
        self.input_var.set("")
        self.entry.focus_set()

    def sanitize_filename(self, text):
        text = re.sub(r'[\\/:*?"<>|]', '_', text)
        return text.strip()

    def on_rename(self, event=None):
        new_name = self.input_var.get().strip()
        if not new_name:
            return

        safe_name = self.sanitize_filename(new_name)
        current_file = self.files[self.current_index]

        try:
            suffix = current_file.name.split('_')[-1]
            new_filename = f"{safe_name}_{suffix}"
            new_path = self.directory / new_filename

            os.rename(current_file, new_path)
            print(f"重命名: {current_file.name} -> {new_filename}")
            self.current_index += 1
            self.load_image()
        except OSError as e:
            messagebox.showerror("错误", f"重命名失败: {e}")

    def on_skip(self):
        self.current_index += 1
        self.load_image()


def main():
    root = tk.Tk()
    if not os.path.exists(OUTPUT_CARDS_DIR):
        print(f"目录 {OUTPUT_CARDS_DIR} 不存在")
        return

    app = ManualRenamer(root, OUTPUT_CARDS_DIR)
    root.mainloop()


if __name__ == "__main__":
    main()