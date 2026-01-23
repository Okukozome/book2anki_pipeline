import os
import tkinter as tk
import re
from PIL import Image, ImageTk
from pathlib import Path

OUTPUT_CARDS_DIR = "final_cards"


class ManualRenamer:
    def __init__(self, root):
        self.root = root
        self.directory = Path(OUTPUT_CARDS_DIR)
        self.files = sorted(list(self.directory.glob("Unknown_*.png")),
                            key=lambda f: int(f.stem.split('_')[-1]) if '_' in f.stem else 0)
        self.current_index = 0

        self.img_label = tk.Label(root, bg="#f0f0f0")
        self.img_label.pack(expand=True, fill="both")
        self.input_var = tk.StringVar()
        self.entry = tk.Entry(root, textvariable=self.input_var, font=("Arial", 14))
        self.entry.pack()
        self.entry.bind("<Return>", self.on_rename)
        self.load_image()

    def load_image(self):
        if self.current_index >= len(self.files): self.root.destroy(); return
        img = Image.open(self.files[self.current_index])
        ratio = 780 / img.size[0]
        img = img.resize((780, int(img.size[1] * ratio)), Image.Resampling.LANCZOS)
        if img.size[1] > 500: img = img.crop((0, 0, 780, 500))

        self.tk_image = ImageTk.PhotoImage(img)
        self.img_label.config(image=self.tk_image)
        self.input_var.set("");
        self.entry.focus_set()

    def on_rename(self, event=None):
        name = re.sub(r'[\\/:*?"<>|]', '_', self.input_var.get().strip())
        if not name: return
        f = self.files[self.current_index]
        os.rename(f, f.parent / f"{name}_{f.name.split('_')[-1]}")
        self.current_index += 1;
        self.load_image()


if __name__ == "__main__":
    root = tk.Tk();
    app = ManualRenamer(root);
    root.mainloop()