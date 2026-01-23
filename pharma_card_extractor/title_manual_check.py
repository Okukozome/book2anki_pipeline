import time
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path

IMAGE_DIR = "check_titles_dir"
FRAME_INTERVAL = 0.2

class DrugTitleViewer:
    def __init__(self, root):
        self.root = root
        self.image_files = self.load_file_list()
        self.current_index = 0
        self.last_action_time = 0

        self.info_label = tk.Label(root, font=("Arial", 12, "bold"))
        self.info_label.pack(side="top", fill="x")
        self.img_label = tk.Label(root, bg="#333333")
        self.img_label.pack(expand=True, fill="both")

        root.bind("<Left>", self.prev_image)
        root.bind("<Right>", self.next_image)
        self.show_current()

    def load_file_list(self):
        p = Path(IMAGE_DIR)
        files = list(p.glob("*.png"))
        try: files.sort(key=lambda x: int(x.stem))
        except: files.sort()
        return files

    def show_current(self):
        fpath = self.image_files[self.current_index]
        self.info_label.config(text=f"{self.current_index + 1}/{len(self.image_files)} - {fpath.name}")
        tk_img = ImageTk.PhotoImage(Image.open(fpath))
        self.img_label.config(image=tk_img)
        self.img_label.image = tk_img

    def navigate(self, delta):
        now = time.time()
        if now - self.last_action_time > FRAME_INTERVAL:
            self.current_index = max(0, min(len(self.image_files)-1, self.current_index + delta))
            self.show_current()
            self.last_action_time = now

    def next_image(self, event=None): self.navigate(1)
    def prev_image(self, event=None): self.navigate(-1)

if __name__ == "__main__":
    root = tk.Tk()
    app = DrugTitleViewer(root)
    root.mainloop()