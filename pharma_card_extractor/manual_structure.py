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
            # 延迟一点显示弹窗，以免阻塞主界面初始化
            self.root.after(100, lambda: messagebox.showinfo("提示", f"{IMAGE_DIR} 目录下没有找到 png 图片"))

    def get_file_list(self):
        if not self.image_dir.exists():
            return []
        files = list(self.image_dir.glob("*.png"))
        try:
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
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def save_presets(self):
        with open(PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, ensure_ascii=False, indent=2)
        self.update_preset_labels()

    def setup_ui(self):
        # 主布局：左右分栏
        # sashrelief="raised" 让分割线更明显
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5, sashrelief="raised")
        self.paned.pack(fill=tk.BOTH, expand=True)

        # --- 左侧：图片滚动区域 ---
        # 确保左侧 Frame 高度和宽度能够被 PanedWindow 正确管理
        self.left_frame = tk.Frame(self.paned, bg="#333", width=LEFT_PANEL_WIDTH)

        # minsize: 最小宽度, stretch="always": 允许随窗口拉伸
        self.paned.add(self.left_frame, minsize=400, width=LEFT_PANEL_WIDTH, stretch="always")

        self.canvas = tk.Canvas(self.left_frame, bg="#333")
        self.v_scroll = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self.left_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        # expand=True 确保 Canvas 填满 Frame 剩余空间
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

        # 增加 Treeview 的滚动条
        self.tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # 详细文本显示 (用于检查完整内容)
        self.detail_text = tk.Text(self.right_frame, height=10, bg="#fff", font=("Consolas", 10))
        self.detail_text.pack(fill="x", padx=10, pady=10)
        self.detail_text.insert("1.0", "此处显示选中的JSON结构预览...")
        self.detail_text.config(state="disabled")

        # 底部：预设状态栏
        self.status_frame = tk.Frame(self.root, bg="#e0e0e0", height=30)
        self.status_frame.pack(side="bottom", fill="x")
        self.preset_label = tk.Label(self.status_frame, text="", bg="#e0e0e0", font=("Arial", 9))
        self.preset_label.pack(side="left", padx=10)

        # 增加操作提示
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
        # 导航
        self.root.bind("<Left>", self.prev_card)
        self.root.bind("<Right>", self.next_card)
        self.root.bind("<Return>", self.save_and_next)

        # 绑定 Ctrl+X 清空数据
        self.root.bind("<Control-x>", self.clear_current_data)

        # 滚轮支持
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # 1-9: 添加一级标题
        # Ctrl+1-9: 设置预设
        # Ctrl+Alt+1-9: 编辑二级标题
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
        self.current_filename = fpath.stem  # 不含后缀的文件名作为Key

        self.info_label.config(text=f"[{self.current_idx + 1}/{len(self.files)}] {fpath.name}")

        try:
            img = Image.open(fpath)
            # 自适应宽度
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
        # 结构: [ {"title": "标题", "items": ["子项1", ...]} ]
        self.current_struct = self.data.get(self.current_filename, [])
        self.refresh_tree()

    def refresh_tree(self):
        # 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 填充树
        for idx, section in enumerate(self.current_struct):
            h1 = section.get('title', 'Unknown')
            items = section.get('items', [])
            item_id = self.tree.insert("", "end", text=h1, values=(f"{len(items)} 项",))
            for sub in items:
                self.tree.insert(item_id, "end", text=sub, values=("",))

            # 默认展开
            self.tree.item(item_id, open=True)

        # 更新JSON预览
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", json.dumps(self.current_struct, ensure_ascii=False, indent=2))
        self.detail_text.config(state="disabled")

    # --- 逻辑操作 ---

    def clear_current_data(self, event=None):
        """清空当前图片的所有录入数据"""
        if not self.current_struct:
            return  # 已经是空的，不需要操作

        if messagebox.askyesno("确认操作", "确定要清空当前图片的所有录入信息吗？\n此操作不可撤销。"):
            self.current_struct = []
            self.save_current_struct_memory()
            self.refresh_tree()
            # 可以在底部状态栏给个反馈
            current_text = self.preset_label.cget("text")
            self.preset_label.config(text="已清空当前数据", fg="red")
            self.root.after(2000, lambda: self.preset_label.config(text=current_text, fg="black"))

    def set_preset(self, idx):
        # 设置快捷键映射
        key = str(idx)
        current_val = self.presets.get(key, "")
        d = CustomDialog(self.root, f"设置快捷键 {idx}", "请输入一级标题名称:", initialvalue=current_val)
        if d.result:
            self.presets[key] = d.result.strip()
            self.save_presets()

    def add_h1_by_preset(self, idx):
        # 按 1-9 添加一级标题
        key = str(idx)
        title = self.presets.get(key)
        if not title:
            messagebox.showwarning("未设置", f"快捷键 {idx} 尚未设置标题，请先按 Ctrl+{idx} 设置。")
            return

        # 检查是否存在
        for section in self.current_struct:
            if section['title'] == title:
                # 如果已存在，闪烁一下或提示，这里直接返回
                return

        self.current_struct.append({"title": title, "items": []})
        self.save_current_struct_memory()
        self.refresh_tree()

    def edit_h2_by_preset(self, idx):
        # 按 Ctrl+Alt+1-9 编辑二级标题
        key = str(idx)
        title = self.presets.get(key)
        if not title:
            messagebox.showwarning("未设置", f"快捷键 {idx} 尚未设置标题。")
            return

        # 找到对应的一级标题块，如果没有则自动创建
        target_section = None
        for section in self.current_struct:
            if section['title'] == title:
                target_section = section
                break

        if not target_section:
            target_section = {"title": title, "items": []}
            self.current_struct.append(target_section)

        # 准备初始文本
        initial_text = "\n".join(target_section['items'])

        d = CustomDialog(self.root, f"录入: {title}", "输入二级标题 (每行一个):", initialvalue=initial_text,
                         multiline=True)
        if d.result is not None:
            # 处理结果：按行分割，去除空行
            lines = [line.strip() for line in d.result.split('\n') if line.strip()]
            target_section['items'] = lines
            self.save_current_struct_memory()
            self.refresh_tree()

    def save_current_struct_memory(self):
        # 仅更新内存中的 total data，不存盘
        self.data[self.current_filename] = self.current_struct

    def save_and_next(self, event=None):
        self.save_data()  # 存盘
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