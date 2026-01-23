import os
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path

OUTPUT_CARDS_DIR = "final_cards"


class VisualChecker:
    def __init__(self, root):
        self.root = root
        self.directory = Path(OUTPUT_CARDS_DIR)
        self.files = self.get_valid_files()
        self.current_index = 0

        self.img_label = tk.Label(root, bg="#f0f0f0")
        self.img_label.pack(expand=True, fill="both")
        self.filename_label = tk.Label(root, font=("Arial", 24, "bold"))
        self.filename_label.pack()

        root.bind('<Left>', self.prev_image)
        root.bind('<Right>', self.next_image)
        root.bind('<Return>', self.mark_as_unknown)
        self.load_image()

    def get_valid_files(self):
        files = [f for f in self.directory.glob("*.png") if not f.name.lower().startswith("unknown")]
        files.sort(key=lambda f: int(f.stem.split('_')[-1]) if '_' in f.stem else 0)
        return files

    def load_image(self):
        if not self.files: self.root.destroy(); return
        current_file = self.files[self.current_index]
        self.filename_label.config(text=current_file.stem.rsplit('_', 1)[0])

        img = Image.open(current_file)
        ratio = 860 / img.size[0]
        img = img.resize((860, int(img.size[1] * ratio)), Image.Resampling.LANCZOS)
        if img.size[1] > 550: img = img.crop((0, 0, 860, 550))

        self.tk_image = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.tk_image)

    def next_image(self, event=None):
        if self.current_index < len(self.files) - 1:
            self.current_index += 1;
            self.load_image()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.current_index -= 1;
            self.load_image()

    def mark_as_unknown(self, event=None):
        f = self.files[self.current_index]
        new_path = f.parent / f"Unknown_{f.name.split('_')[-1]}"
        os.rename(f, new_path)
        del self.files[self.current_index]
        self.load_image()


if __name__ == "__main__":
    root = tk.Tk()
    app = VisualChecker(root)
    root.mainloop()