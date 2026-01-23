import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from PIL import Image, ImageTk
from pathlib import Path
import json
import os

# 配置
IMAGE_DIR = "final_cards"
DATA_FILE = "structure_data.json"
PRESET_FILE = "structure_presets.json"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
LEFT_PANEL_WIDTH = 750  # 图片区域默认宽度
Image.MAX_IMAGE_PIXELS = None


class CustomDialog(simpledialog.Dialog):
    def __init__(self, parent, title, prompt, initialvalue="", multiline=False):
        self.prompt = prompt
        self.initialvalue = initialvalue
        self.multiline = multiline
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text=self.prompt).pack(pady=5)
        if self.multiline:
            # 多行模式提示
            tk.Label(master, text="(Enter 换行，Ctrl+Enter 提交)", font=("Arial", 8), fg="gray").pack()

            self.text_entry = tk.Text(master, height=10, width=40)
            self.text_entry.pack(padx=5, pady=5)
            self.text_entry.insert("1.0", self.initialvalue)

            def on_return(event):
                self.text_entry.insert("insert", "\n")
                return "break"

            self.text_entry.bind("<Return>", on_return)
            self.text_entry.bind("<Control-Return>", self.ok)

            return self.text_entry
        else:
            self.entry = tk.Entry(master, width=40)
            self.entry.pack(padx=5, pady=5)
            self.entry.insert(0, self.initialvalue)
            return self.entry

    def apply(self):
        if self.multiline:
            self.result = self.text_entry.get("1.0", "end-1c")
        else:
            self.result = self.entry.get()


class StructureExtractor:
    def __init__(self, root):
        self.root = root
        self.root.title("结构化信息提取工具")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.image_dir = Path(IMAGE_DIR)

        # 确保目录存在
        if not self.image_dir.exists():
            try:
                self.image_dir.mkdir(parents=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建目录: {e}")

        self.files = self.get_file_list()
        self.current_idx = 0
        self.zoom_level = 1.0

        # 数据加载
        self.data = self.load_json(DATA_FILE)
        self.presets = self.load_json(PRESET_FILE)

        # 初始化UI
        self.setup_ui()
        self.bind_keys()

        if self.files:
            self.load_current_card()
        else:
            self.root.after(100, lambda: messagebox.showinfo("提示", f"{IMAGE_DIR} 目录下没有找到 png 图片"))

    def get_file_list(self):
        if not self.image_dir.exists():
            return []
        files = list(self.image_dir.glob("*.png"))
        try:
            # 优先按数字后缀排序
            files.sort(key=lambda x: int(x.stem.split('_')[-1]) if '_' in x.stem and x.stem.split('_')[
                -1].isdigit() else x.name)
        except:
            files.sort(key=lambda x: x.name)
        return files

    def load_json(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_data(self):
        """
        保存数据到JSON文件。
        改进逻辑：
        1. 自动将所有未录入的文件补全为 []
        2. 按照数字顺序 (drug_2 < drug_10) 对 Key 进行排序
        """
        # 1. 补全：确保目录下的所有文件都在 data 中
        if self.files:
            for f in self.files:
                if f.stem not in self.data:
                    self.data[f.stem] = []

        # 2. 排序：定义排序 Key 函数
        def sort_key(item):
            key = item[0]
            # 尝试分割 "drug_10" 提取数字 10
            if '_' in key:
                parts = key.split('_')
                if parts[-1].isdigit():
                    # 优先级 0: 能够提取出数字的，按数字大小排序
                    return (0, int(parts[-1]))

            # 优先级 1: 无法提取数字的，按文件名原本的字符串排序
            return (1, key)

        # 执行排序
        try:
            sorted_items = sorted(self.data.items(), key=sort_key)
            self.data = dict(sorted_items)
        except Exception as e:
            print(f"排序时发生非致命错误: {e}")
            # 如果排序失败，保持原样，避免丢失数据

        # 3. 写入文件
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def save_presets(self):
        with open(PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, ensure_ascii=False, indent=2)
        self.update_preset_labels()

    def setup_ui(self):
        # 主布局：左右分栏
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, sashrelief="raised")
        self.paned.pack(fill=tk.BOTH, expand=True)

        # --- 左侧：图片滚动区域 ---
        self.left_frame = tk.Frame(self.paned, bg="#333", width=LEFT_PANEL_WIDTH)
        self.paned.add(self.left_frame, minsize=400, width=LEFT_PANEL_WIDTH, stretch="always")

        self.canvas = tk.Canvas(self.left_frame, bg="#333")
        self.v_scroll = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.left_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        # --- 右侧：信息录入和显示 ---
        self.right_frame = tk.Frame(self.paned, bg="#f0f0f0")
        self.paned.add(self.right_frame, minsize=300, stretch="always")

        # 顶部信息
        self.info_label = tk.Label(self.right_frame, text="", font=("Arial", 12, "bold"), bg="#f0f0f0", anchor="w")
        self.info_label.pack(fill="x", padx=10, pady=10)

        # 结构显示区域 (Treeview)
        self.tree_frame = tk.Frame(self.right_frame)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("content",)
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="结构 (一级标题)")
        self.tree.heading("content", text="内容 (二级标题数量)")
        self.tree.column("#0", width=200)
        self.tree.column("content", width=100, anchor="center")

        self.tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # 详细文本显示
        self.detail_text = tk.Text(self.right_frame, height=10, bg="#fff", font=("Consolas", 10))
        self.detail_text.pack(fill="x", padx=10, pady=10)
        self.detail_text.insert("1.0", "此处显示选中的JSON结构预览...")
        self.detail_text.config(state="disabled")

        # 底部：预设状态栏
        self.status_frame = tk.Frame(self.root, bg="#e0e0e0", height=30)
        self.status_frame.pack(side="bottom", fill="x")
        self.preset_label = tk.Label(self.status_frame, text="", bg="#e0e0e0", font=("Arial", 9))
        self.preset_label.pack(side="left", padx=10)

        tk.Label(self.status_frame, text="Ctrl+X: 清空当前 | Enter: 保存并下一个", bg="#e0e0e0", fg="blue").pack(
            side="right", padx=10)

        self.update_preset_labels()

    def update_preset_labels(self):
        text = "快捷键映射 (Ctrl+数字设置):  "
        for i in range(1, 10):
            key = str(i)
            val = self.presets.get(key, "未设置")
            text += f"[{i}:{val}]  "
        self.preset_label.config(text=text)

    def bind_keys(self):
        self.root.bind("<Left>", self.prev_card)
        self.root.bind("<Right>", self.next_card)
        self.root.bind("<Return>", self.save_and_next)
        self.root.bind("<Control-x>", self.clear_current_data)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        for i in range(1, 10):
            self.root.bind(f"{i}", lambda event, idx=i: self.add_h1_by_preset(idx))
            self.root.bind(f"<Control-Key-{i}>", lambda event, idx=i: self.set_preset(idx))
            self.root.bind(f"<Control-Alt-Key-{i}>", lambda event, idx=i: self.edit_h2_by_preset(idx))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def load_current_card(self):
        if not self.files: return

        # 1. 显示图片
        fpath = self.files[self.current_idx]
        self.current_filename = fpath.stem

        self.info_label.config(text=f"[{self.current_idx + 1}/{len(self.files)}] {fpath.name}")

        try:
            img = Image.open(fpath)
            base_width = LEFT_PANEL_WIDTH
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img_resized = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

            self.tk_img = ImageTk.PhotoImage(img_resized)
            self.canvas.config(scrollregion=(0, 0, base_width, h_size))
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
            self.canvas.yview_moveto(0)
        except Exception as e:
            messagebox.showerror("图片加载错误", f"无法加载图片: {e}")

        # 2. 加载或初始化数据结构
        # 如果当前文件在内存中尚未存在，直接初始化为空列表，确保它"占位"
        if self.current_filename not in self.data:
            self.data[self.current_filename] = []

        self.current_struct = self.data[self.current_filename]
        self.refresh_tree()

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for idx, section in enumerate(self.current_struct):
            h1 = section.get('title', 'Unknown')
            items = section.get('items', [])
            item_id = self.tree.insert("", "end", text=h1, values=(f"{len(items)} 项",))
            for sub in items:
                self.tree.insert(item_id, "end", text=sub, values=("",))
            self.tree.item(item_id, open=True)

        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", json.dumps(self.current_struct, ensure_ascii=False, indent=2))
        self.detail_text.config(state="disabled")

    def clear_current_data(self, event=None):
        if not self.current_struct:
            return

        if messagebox.askyesno("确认操作", "确定要清空当前图片的所有录入信息吗？\n此操作不可撤销。"):
            self.current_struct.clear()  # 直接清空列表对象
            # 不需要重新赋值给 self.data，因为列表是引用传递
            self.refresh_tree()

            current_text = self.preset_label.cget("text")
            self.preset_label.config(text="已清空当前数据", fg="red")
            self.root.after(2000, lambda: self.preset_label.config(text=current_text, fg="black"))

    def set_preset(self, idx):
        key = str(idx)
        current_val = self.presets.get(key, "")
        d = CustomDialog(self.root, f"设置快捷键 {idx}", "请输入一级标题名称:", initialvalue=current_val)
        if d.result:
            self.presets[key] = d.result.strip()
            self.save_presets()

    def add_h1_by_preset(self, idx):
        key = str(idx)
        title = self.presets.get(key)
        if not title:
            messagebox.showwarning("未设置", f"快捷键 {idx} 尚未设置标题，请先按 Ctrl+{idx} 设置。")
            return

        for section in self.current_struct:
            if section['title'] == title:
                return

        self.current_struct.append({"title": title, "items": []})
        self.save_current_struct_memory()
        self.refresh_tree()

    def edit_h2_by_preset(self, idx):
        key = str(idx)
        title = self.presets.get(key)
        if not title:
            messagebox.showwarning("未设置", f"快捷键 {idx} 尚未设置标题。")
            return

        target_section = None
        for section in self.current_struct:
            if section['title'] == title:
                target_section = section
                break

        if not target_section:
            target_section = {"title": title, "items": []}
            self.current_struct.append(target_section)

        initial_text = "\n".join(target_section['items'])

        d = CustomDialog(self.root, f"录入: {title}", "输入二级标题 (每行一个):", initialvalue=initial_text,
                         multiline=True)
        if d.result is not None:
            lines = [line.strip() for line in d.result.split('\n') if line.strip()]
            target_section['items'] = lines
            self.save_current_struct_memory()
            self.refresh_tree()

    def save_current_struct_memory(self):
        # 显式更新内存（虽然 self.current_struct 引用通常已足够，但为了保险起见）
        self.data[self.current_filename] = self.current_struct

    def save_and_next(self, event=None):
        """保存并跳转下一张"""
        self.save_current_struct_memory()  # 确保当前改动已同步
        self.save_data()  # 触发补全、排序和写入硬盘
        self.next_card()

    def next_card(self, event=None):
        if self.current_idx < len(self.files) - 1:
            self.current_idx += 1
            self.load_current_card()
        else:
            messagebox.showinfo("完成", "已经是最后一张了！")

    def prev_card(self, event=None):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_current_card()


if __name__ == "__main__":
    root = tk.Tk()
    app = StructureExtractor(root)
    root.mainloop()