from __future__ import annotations

import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import xml.etree.ElementTree as ET
import textwrap

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageTk = None
    ImageDraw = None
    ImageFont = None

SYSTEMS = [
    "SMS", "arcade", "atari2600", "atarilynx", "cps1", "cps2", "cps3",
    "gamegear", "gb", "gba", "gbc", "genesis", "megadrive", "nes",
    "pcengine", "psp", "psx", "snes", "wonder",
]
EXT_SYSTEM = {
    ".sms": "SMS", ".a26": "atari2600", ".lnx": "atarilynx",
    ".gg": "gamegear", ".gb": "gb", ".gba": "gba", ".gbc": "gbc",
    ".md": "megadrive", ".gen": "genesis", ".nes": "nes",
    ".pce": "pcengine", ".iso": "psp", ".cso": "psp", ".pbp": "psp",
    ".cue": "psx", ".chd": "psx", ".bin": "psx", ".sfc": "snes",
    ".smc": "snes", ".ws": "wonder", ".wsc": "wonder",
}
ROM_EXTS = {
    ".zip", ".7z", ".rar", ".sms", ".a26", ".bin", ".lnx", ".gg",
    ".gb", ".gba", ".gbc", ".md", ".gen", ".nes", ".pce", ".iso",
    ".cso", ".pbp", ".cue", ".chd", ".sfc", ".smc", ".ws", ".wsc",
    ".n64", ".z64", ".v64", ".rom", ".img",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}

# Generic illustrated hardware silhouettes are drawn locally; no image download is needed.
SYSTEM_STYLE = {
    "nes": ("#202d49", "#e9edf5", "NES / FAMICOM", "console"),
    "snes": ("#40305f", "#eee8ff", "SUPER NINTENDO", "console"),
    "psx": ("#263746", "#e4e9ee", "PLAYSTATION", "playstation"),
    "psp": ("#244c66", "#e7f7ff", "PLAYSTATION PORTABLE", "handheld"),
    "gb": ("#334b3a", "#e6f2c7", "GAME BOY", "handheld"),
    "gbc": ("#403b6b", "#f0eaff", "GAME BOY COLOR", "handheld"),
    "gba": ("#35466d", "#e9efff", "GAME BOY ADVANCE", "handheld"),
    "gamegear": ("#3f4b55", "#eaf0f4", "GAME GEAR", "handheld"),
    "genesis": ("#303744", "#e6e9ef", "SEGA GENESIS", "console"),
    "megadrive": ("#303744", "#e6e9ef", "MEGA DRIVE", "console"),
    "SMS": ("#34485d", "#e8f2fa", "SEGA MASTER SYSTEM", "console"),
    "wonder": ("#37514d", "#e8f7ee", "WONDERSWAN", "handheld"),
    "pcengine": ("#4c3545", "#f7eaf0", "PC ENGINE", "console"),
    "atari2600": ("#473a32", "#f7eadb", "ATARI 2600", "console"),
    "atarilynx": ("#3c4650", "#eaf0f5", "ATARI LYNX", "handheld"),
    "arcade": ("#4a2f36", "#fff0f2", "ARCADE", "arcade"),
    "cps1": ("#4a2f36", "#fff0f2", "CAPCOM CPS-1", "arcade"),
    "cps2": ("#4a2f36", "#fff0f2", "CAPCOM CPS-2", "arcade"),
    "cps3": ("#4a2f36", "#fff0f2", "CAPCOM CPS-3", "arcade"),
}

def xml_text(parent, tag, value):
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child

def _font(size, bold=False):
    if ImageFont is None:
        return None
    candidates = (
        [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"]
        if bold else
        [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()

def create_placeholder_image(output_path: Path, title: str, system: str):
    """Create a system-themed console illustration with the ROM title."""
    if Image is None:
        raise RuntimeError("代替画像の生成にはPillowが必要です。")
    bg, fg, hardware_label, kind = SYSTEM_STYLE.get(
        system, ("#303b50", "#edf2fa", system.upper(), "console")
    )
    width, height = 640, 400
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    # Subtle background pattern and frame.
    for x in range(0, width, 40):
        draw.line((x, 0, x, height), fill=bg, width=1)
    for y in range(0, height, 40):
        draw.line((0, y, width, y), fill=bg, width=1)
    draw.rounded_rectangle((14, 14, width - 15, height - 15), radius=22,
                           outline=fg, width=3)

    # Stylized hardware, not a photograph or a copied product image.
    if kind == "handheld":
        draw.rounded_rectangle((205, 55, 435, 210), radius=28, fill="#20242b", outline=fg, width=4)
        draw.rounded_rectangle((235, 77, 405, 150), radius=8, fill="#8db4b5", outline="#111820", width=3)
        draw.rectangle((249, 88, 391, 139), fill="#577f87")
        draw.rectangle((270, 108, 370, 120), fill="#a8c9c0")
        draw.ellipse((386, 165, 407, 186), fill="#b74f59", outline=fg, width=2)
        draw.ellipse((357, 178, 378, 199), fill="#d4b25d", outline=fg, width=2)
        draw.rectangle((229, 166, 267, 177), fill=fg)
        draw.rectangle((242, 153, 254, 190), fill=fg)
    elif kind == "playstation":
        draw.rounded_rectangle((185, 75, 455, 178), radius=18, fill="#d6d9dc", outline=fg, width=4)
        draw.ellipse((216, 104, 260, 148), fill="#8b929b", outline="#353b43", width=3)
        draw.ellipse((379, 104, 423, 148), fill="#8b929b", outline="#353b43", width=3)
        draw.line((238, 114, 238, 138), fill="#303842", width=4)
        draw.line((226, 126, 250, 126), fill="#303842", width=4)
        draw.ellipse((389, 113, 400, 124), fill="#9b5362")
        draw.ellipse((402, 128, 413, 139), fill="#648aab")
        draw.rounded_rectangle((295, 105, 345, 150), radius=6, fill="#303842")
    elif kind == "arcade":
        draw.rounded_rectangle((225, 50, 415, 220), radius=14, fill="#24232c", outline=fg, width=4)
        draw.rectangle((250, 72, 390, 145), fill="#9b6479", outline=fg, width=3)
        draw.polygon([(265, 130), (290, 91), (320, 130)], fill="#f0c36a")
        draw.ellipse((330, 91, 372, 133), outline="#e7edf6", width=5)
        draw.rectangle((245, 159, 395, 180), fill="#55525f")
        draw.ellipse((285, 164, 301, 180), fill="#c95f65")
        draw.ellipse((315, 164, 331, 180), fill="#d8b85e")
    else:
        draw.rounded_rectangle((180, 80, 460, 185), radius=18, fill="#c5cbd1", outline=fg, width=4)
        draw.rectangle((205, 95, 435, 113), fill="#737d89")
        draw.ellipse((218, 128, 258, 168), fill="#343b45")
        draw.rectangle((231, 137, 245, 159), fill=fg)
        draw.rectangle((222, 144, 254, 152), fill=fg)
        draw.ellipse((376, 130, 396, 150), fill="#b6535f")
        draw.ellipse((403, 148, 423, 168), fill="#d3b15c")
        draw.rectangle((295, 143, 340, 165), fill="#707a86")

    label_font = _font(19, True)
    title_font = _font(28, True)
    draw.text((width // 2, 235), hardware_label, font=label_font, fill=fg, anchor="mm")

    # Wrap long titles to fit. Use the filename stem as the display title.
    clean_title = title.strip() or "Unknown title"
    max_chars = 30
    lines = textwrap.wrap(clean_title, width=max_chars) or [clean_title]
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1] = lines[-1][:max_chars - 3] + "..."
    while title_font.size > 17 and any(draw.textbbox((0, 0), line, font=title_font)[2] > 570 for line in lines):
        title_font = _font(title_font.size - 2, True)
    panel_top = 268
    draw.rounded_rectangle((36, panel_top, width - 36, 366), radius=16, fill="#111820", outline=fg, width=2)
    line_height = 32
    total_height = len(lines) * line_height
    y = panel_top + (98 - total_height) // 2
    for line in lines:
        draw.text((width // 2, y), line, font=title_font, fill="#ffffff", anchor="mt")
        y += line_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")

class ImagePicker(tk.Toplevel):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.title("画像をプレビューして選択")
        self.geometry("760x500")
        self.minsize(620, 400)
        self.transient(parent)
        self.grab_set()
        self.result = None
        self.preview_image = None
        self.files = []

        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="画像フォルダを開く...", command=self.choose_folder).pack(side="left")
        ttk.Button(bar, text="画像ファイルを追加...", command=self.add_file).pack(side="left", padx=6)

        body = ttk.Frame(self, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        self.listbox = tk.Listbox(left, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self.show_preview)
        self.listbox.bind("<Double-Button-1>", self.accept)

        right = ttk.LabelFrame(body, text="プレビュー", padding=8)
        right.pack(side="right", fill="both", padx=(10, 0))
        self.preview = ttk.Label(right, text="画像を選択してください", anchor="center", width=34)
        self.preview.pack(fill="both", expand=True)
        self.filename = ttk.Label(right, text="", wraplength=240)
        self.filename.pack(fill="x", pady=(8, 0))

        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="キャンセル", command=self.destroy).pack(side="right")
        ttk.Button(bottom, text="この画像を選択", command=self.accept).pack(side="right", padx=6)

        if Image is None:
            messagebox.showerror("画像プレビューを利用できません",
                                 "Pillowが読み込めません。EXEを再ビルドするか、Pillowをインストールしてください。",
                                 parent=self)
            self.destroy()
            return
        if current and current.is_file():
            self.add_path(current)

    def choose_folder(self):
        folder = filedialog.askdirectory(parent=self, title="画像が保存されているフォルダを選択")
        if not folder:
            return
        paths = sorted((p for p in Path(folder).iterdir()
                        if p.is_file() and p.suffix.lower() in IMAGE_EXTS),
                       key=lambda p: p.name.lower())
        for path in paths:
            self.add_path(path)

    def add_file(self):
        selected = filedialog.askopenfilename(
            parent=self, title="画像ファイルを選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.webp *.gif"),
                       ("すべてのファイル", "*.*")]
        )
        if selected:
            self.add_path(Path(selected))

    def add_path(self, path):
        path = Path(path)
        if path not in self.files:
            self.files.append(path)
            self.listbox.insert("end", str(path))
        index = self.files.index(path)
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.show_preview()

    def show_preview(self, _event=None):
        selected = self.listbox.curselection()
        if not selected:
            return
        path = self.files[selected[0]]
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((300, 330))
                self.preview_image = ImageTk.PhotoImage(img)
            self.preview.configure(image=self.preview_image, text="")
            self.filename.configure(text=path.name)
        except Exception as exc:
            self.preview.configure(image="", text="プレビューを表示できません")
            self.filename.configure(text=f"{path.name}\n{exc}")

    def accept(self, _event=None):
        selected = self.listbox.curselection()
        if not selected:
            messagebox.showinfo("画像未選択", "一覧から画像を選択してください。", parent=self)
            return
        self.result = self.files[selected[0]]
        self.destroy()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PS202 ROM・画像関連付けツール")
        self.geometry("1180x740")
        self.minsize(900, 560)
        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.status_var = tk.StringVar(value="ROMの上位フォルダを選択してください。")
        self.items = []
        self.next_uid = 0
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="ROMの上位フォルダ").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(top, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="参照...", command=self.choose_source).grid(row=0, column=2)
        ttk.Label(top, text="コピー先の roms フォルダ").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(top, textvariable=self.dest_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="参照...", command=self.choose_dest).grid(row=1, column=2)
        top.columnconfigure(1, weight=1)

        actions = ttk.Frame(self, padding=(10, 0, 10, 8))
        actions.pack(fill="x")
        ttk.Button(actions, text="配下のROMを一括読み込み", command=self.load_roms).pack(side="left")
        ttk.Label(actions, text="不要なROMは選択してリストから外せます。").pack(side="left", padx=12)

        columns = ("rom", "folder", "system", "image", "output")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="extended")
        for col, title in [
            ("rom", "ROMファイル"), ("folder", "元フォルダ"),
            ("system", "システム / 出力先"), ("image", "関連付け画像"),
            ("output", "画像の出力名")
        ]:
            self.tree.heading(col, text=title)
        self.tree.column("rom", width=220, anchor="w")
        self.tree.column("folder", width=300, anchor="w")
        self.tree.column("system", width=150, anchor="center")
        self.tree.column("image", width=300, anchor="w")
        self.tree.column("output", width=180, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", self.on_double_click)

        controls = ttk.Frame(self, padding=10)
        controls.pack(fill="x")
        ttk.Button(controls, text="選択ROMの画像を選ぶ...", command=self.choose_image).pack(side="left")
        ttk.Button(controls, text="画像を解除", command=self.clear_image).pack(side="left", padx=5)
        ttk.Button(controls, text="選択ROMをリストから削除", command=self.remove_selected).pack(side="left", padx=5)
        ttk.Button(controls, text="選択フォルダ内をまとめて削除", command=self.remove_folder_items).pack(side="left", padx=5)
        ttk.Button(controls, text="リストを再読み込み", command=self.load_roms).pack(side="left", padx=5)
        ttk.Button(controls, text="生成・コピーを実行", command=self.execute).pack(side="right")

        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=5).pack(fill="x", side="bottom")

    def choose_source(self):
        p = filedialog.askdirectory(title="ROMの上位フォルダを選択")
        if p:
            self.source_var.set(p)
            self.load_roms()

    def choose_dest(self):
        p = filedialog.askdirectory(title="コピー先の roms フォルダを選択")
        if p:
            self.dest_var.set(p)

    def load_roms(self):
        root = Path(self.source_var.get().strip().strip('"'))
        if not root.is_dir():
            messagebox.showerror("入力エラー", "有効なROM保存元フォルダを指定してください。")
            return
        self.items.clear()
        self.tree.delete(*self.tree.get_children())
        self.next_uid = 0
        files = sorted((p for p in root.rglob("*")
                        if p.is_file() and p.suffix.lower() in ROM_EXTS),
                       key=lambda p: str(p.relative_to(root)).lower())
        for path in files:
            rel = path.relative_to(root)
            if rel.parent == Path("."):
                folder = ""
                system = EXT_SYSTEM.get(path.suffix.lower(), "")
            else:
                folder = str(rel.parent)
                top_folder = rel.parts[0]
                system = top_folder if top_folder in SYSTEMS else EXT_SYSTEM.get(path.suffix.lower(), "")
            item = {"uid": self.next_uid, "path": path, "rel": rel,
                    "folder": folder, "system": system, "output_folder": None, "image": None}
            self.next_uid += 1
            self.items.append(item)
            self._insert(item)
        self.status_var.set(f"{len(self.items)}件のROMを読み込みました。不要な項目はリストから削除してください。")
        if not files:
            messagebox.showinfo("ROMなし", "配下に対応する拡張子のROMが見つかりませんでした。")

    def _insert(self, item):
        path, image = item["path"], item["image"]
        output = path.stem + image.suffix.lower() if image else "(自動生成)"
        self.tree.insert("", "end", iid=str(item["uid"]), values=(
            path.name, item["folder"] or "（上位フォルダ直下）",
            item["system"] or "未指定", str(image) if image else "（未指定・自動生成）", output
        ))

    def _selected_items(self):
        selected = set(self.tree.selection())
        return [item for item in self.items if str(item["uid"]) in selected]

    def _refresh_row(self, item):
        iid = str(item["uid"])
        if iid not in self.tree.get_children(""):
            return
        path, image = item["path"], item["image"]
        self.tree.item(iid, values=(
            path.name, item["folder"] or "（上位フォルダ直下）",
            item["system"] or "未指定", str(image) if image else "（未指定・自動生成）",
            path.stem + image.suffix.lower() if image else "(自動生成)"
        ))

    def choose_image(self):
        selected = self._selected_items()
        if len(selected) != 1:
            messagebox.showinfo("選択", "画像を関連付けるROMを1件選択してください。")
            return
        picker = ImagePicker(self, selected[0]["image"])
        self.wait_window(picker)
        if picker.result:
            selected[0]["image"] = picker.result
            self._refresh_row(selected[0])

    def clear_image(self):
        selected = self._selected_items()
        if not selected:
            messagebox.showinfo("選択", "画像を解除するROMを選択してください。")
            return
        for item in selected:
            item["image"] = None
            self._refresh_row(item)

    def remove_selected(self):
        selected = self._selected_items()
        if not selected:
            messagebox.showinfo("選択", "リストから外すROMを選択してください。")
            return
        if not messagebox.askyesno("リストから削除", f"{len(selected)}件を処理対象から外しますか？\n元のROMファイルは削除されません。"):
            return
        uids = {item["uid"] for item in selected}
        self.items = [item for item in self.items if item["uid"] not in uids]
        for uid in uids:
            if str(uid) in self.tree.get_children(""):
                self.tree.delete(str(uid))
        self._update_status()

    def remove_folder_items(self):
        selected = self._selected_items()
        if not selected:
            messagebox.showinfo("選択", "対象にするフォルダ内のROMを1件選択してください。")
            return
        root = Path(self.source_var.get().strip().strip('"'))
        folders = {item["path"].parent for item in selected}
        targets = [item for item in self.items if any(
            item["path"] == folder or folder in item["path"].parents for folder in folders
        )]
        if not targets:
            return
        labels = "\n".join(str(folder.relative_to(root)) if folder != root else "(上位フォルダ直下)" for folder in folders)
        if not messagebox.askyesno("フォルダ内をリストから削除",
                                   f"次のフォルダ配下にあるROM {len(targets)}件を処理対象から外しますか？\n\n{labels}\n\n元のROMファイルは削除されません。"):
            return
        uids = {item["uid"] for item in targets}
        self.items = [item for item in self.items if item["uid"] not in uids]
        for uid in uids:
            if str(uid) in self.tree.get_children(""):
                self.tree.delete(str(uid))
        self._update_status()

    def _update_status(self):
        self.status_var.set(f"処理対象：{len(self.items)}件")

    def on_double_click(self, event):
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        iid = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if column == "#4":
            if iid:
                self.tree.selection_set(iid)
            self.choose_image()
        elif column == "#3" and iid:
            item = next((x for x in self.items if str(x["uid"]) == iid), None)
            if item:
                self._edit_unknown_system(item, iid)

    def _edit_unknown_system(self, item, iid):
        # Every row can change or correct its system/output folder.
        bbox = self.tree.bbox(iid, "#3")
        if not bbox:
            return
        x, y, width, height = bbox
        combo = ttk.Combobox(self.tree, values=SYSTEMS, state="readonly")
        combo.place(x=x, y=y, width=width, height=height)
        combo.set(item.get("output_folder") or item.get("system") or "")
        combo.focus_set()

        def apply(_event=None):
            chosen = combo.get().strip()
            combo.destroy()
            if not chosen:
                return
            item["system"] = chosen
            # An explicit dropdown choice overrides source-folder inference and can be changed later.
            item["output_folder"] = chosen
            self._refresh_row(item)
            self.status_var.set(f"{item['path'].name}: システム／出力先を {chosen} に設定しました。")

        combo.bind("<<ComboboxSelected>>", apply)
        combo.bind("<Escape>", lambda _event: combo.destroy())
        combo.bind("<FocusOut>", lambda _event: combo.destroy())

    def _target_folder(self, item, dest):
        # Explicit assignment from the dropdown takes precedence over source folders.
        if item.get("output_folder"):
            return dest / item["output_folder"]
        rel_parent = item["rel"].parent
        if rel_parent == Path("."):
            if not item["system"]:
                raise ValueError(f"システムが未指定です: {item['path'].name}")
            return dest / item["system"]
        return dest / rel_parent

    def execute(self):
        dest = Path(self.dest_var.get().strip().strip('"'))
        source = Path(self.source_var.get().strip().strip('"'))
        if not self.items:
            messagebox.showerror("実行できません", "処理対象のROMがありません。")
            return
        if Image is None:
            messagebox.showerror("必要なライブラリがありません", "画像処理用のPillowが必要です。EXEを再ビルドしてください。")
            return
        if not source.is_dir() or not dest.is_dir():
            messagebox.showerror("入力エラー", "有効な保存元とコピー先のフォルダを指定してください。")
            return
        if not messagebox.askyesno("最終確認",
            f"リストに残っているROM {len(self.items)}件をコピーし、未指定画像はシステム別の代替画像を自動生成します。\n"
            "フォルダごとに gamelist.xml を生成します。既存ファイルは上書きしません。\n続行しますか？"):
            return

        planned = []
        xml_groups = {}
        reserved = set()
        try:
            for item in self.items:
                if not item["system"]:
                    raise ValueError(
                        f"システム／出力先が未指定です: {item['path'].name}\n"
                        "一覧の「システム / 出力先」欄をダブルクリックして選択してください。"
                    )
                target_dir = self._target_folder(item, dest)
                rom_target = target_dir / item["path"].name
                system = item["system"]
                img_target = (target_dir / "images" / (item["path"].stem + item["image"].suffix.lower())) if item["image"] else (target_dir / "images" / (item["path"].stem + ".png"))
                xml_target = target_dir / "gamelist.xml"
                for target in (rom_target, img_target):
                    key = str(target).casefold()
                    if target.exists():
                        raise FileExistsError(
                            f"出力先に同名ファイルが既に存在します:\n{target}"
                        )
                    if key in reserved:
                        raise FileExistsError(
                            f"複数のROMが同じ出力ファイル名になります。\n"
                            f"ROM名や出力先システムを変更してください:\n{target}"
                        )
                    reserved.add(key)
                planned_item = {"item": item, "target_dir": target_dir, "system": system,
                                "rom_target": rom_target, "img_target": img_target,
                                "xml_target": xml_target}
                planned.append(planned_item)
                xml_groups.setdefault(target_dir, []).append(planned_item)

            for folder in xml_groups:
                xml_path = folder / "gamelist.xml"
                if xml_path.exists():
                    raise FileExistsError(f"既存の gamelist.xml があるため中止します:\n{xml_path}")
                if str(xml_path).casefold() in reserved:
                    raise FileExistsError(f"ROMまたは画像の出力先が gamelist.xml と重複しています:\n{xml_path}")

        except Exception as exc:
            messagebox.showerror("事前確認エラー", f"{exc}\n\nファイルはコピーしていません。")
            return

        try:
            for entry in planned:
                target_dir = entry["target_dir"]
                (target_dir / "images").mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry["item"]["path"], entry["rom_target"])
                if entry["item"]["image"]:
                    shutil.copy2(entry["item"]["image"], entry["img_target"])
                else:
                    create_placeholder_image(entry["img_target"], entry["rom_target"].stem, entry["system"])

            for folder, entries in xml_groups.items():
                root_xml = ET.Element("gameList")
                for entry in entries:
                    item = entry["item"]
                    rom_target = entry["rom_target"]
                    img_target = entry["img_target"]
                    game = ET.SubElement(root_xml, "game")
                    xml_text(game, "gameid", rom_target.stem)
                    xml_text(game, "path", "./" + rom_target.name)
                    xml_text(game, "image", "./images/" + img_target.name)
                    xml_text(game, "video_id", "7")
                    xml_text(game, "class_type", "7")
                    xml_text(game, "game_type", "0")
                    xml_text(game, "timer", entry["system"])
                    xml_text(game, "zh_CN", rom_target.stem)
                    xml_text(game, "en_US", rom_target.stem)
                    xml_text(game, "zh_TW", rom_target.stem)
                    xml_text(game, "ko_KR", rom_target.stem)
                    xml_text(game, "name", rom_target.stem)
                tree = ET.ElementTree(root_xml)
                ET.indent(tree, space="\t")
                xml_path = folder / "gamelist.xml"
                tree.write(xml_path, encoding="utf-8", xml_declaration=True)

            messagebox.showinfo("完了",
                f"処理が完了しました。\nROM: {len(planned)}件\n代替画像の自動生成: {sum(1 for x in planned if not x['item']['image'])}件\n出力フォルダ: {len(xml_groups)}個")
            self.status_var.set(f"完了：ROM {len(planned)}件、代替画像 {sum(1 for x in planned if not x['item']['image'])}件")
        except Exception as exc:
            messagebox.showerror("処理エラー",
                f"処理中にエラーが発生しました。\n{exc}\n一部の出力ファイルが作成されている可能性があります。")
            self.status_var.set("エラーが発生しました。")

if __name__ == "__main__":
    App().mainloop()
