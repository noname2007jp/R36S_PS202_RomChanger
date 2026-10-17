from __future__ import annotations

import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

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

def xml_text(parent, tag, value):
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child

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
                    "folder": folder, "system": system, "image": None}
            self.next_uid += 1
            self.items.append(item)
            self._insert(item)
        self.status_var.set(f"{len(self.items)}件のROMを読み込みました。不要な項目はリストから削除してください。")
        if not files:
            messagebox.showinfo("ROMなし", "配下に対応する拡張子のROMが見つかりませんでした。")

    def _insert(self, item):
        path, image = item["path"], item["image"]
        output = path.stem + image.suffix.lower() if image else ""
        self.tree.insert("", "end", iid=str(item["uid"]), values=(
            path.name, item["folder"] or "（上位フォルダ直下）",
            item["system"] or "未指定", str(image) if image else "（未指定）", output
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
            item["system"] or "未指定", str(image) if image else "（未指定）",
            path.stem + image.suffix.lower() if image else ""
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
        col = self.tree.identify_column(event.x)
        if col == "#4":
            self.choose_image()

    def _target_folder(self, item, dest):
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
        if not source.is_dir() or not dest.is_dir():
            messagebox.showerror("入力エラー", "有効な保存元とコピー先のフォルダを指定してください。")
            return
        if not messagebox.askyesno("最終確認",
            f"リストに残っているROM {len(self.items)}件をコピーし、フォルダごとに gamelist.xml を生成します。\n"
            "既存ファイルは上書きせず、衝突があれば処理を中止します。\n続行しますか？"):
            return

        planned = []
        xml_groups = {}
        reserved = set()
        try:
            for item in self.items:
                target_dir = self._target_folder(item, dest)
                rom_target = target_dir / item["path"].name
                img_target = (target_dir / "images" / (item["path"].stem + item["image"].suffix.lower())) if item["image"] else None
                xml_target = target_dir / "gamelist.xml"
                for target in (rom_target, img_target):
                    if target:
                        key = str(target).casefold()
                        if target.exists() or key in reserved:
                            raise FileExistsError(f"既存または重複する出力先があります:\n{target}")
                        reserved.add(key)
                planned_item = {"item": item, "target_dir": target_dir,
                                "rom_target": rom_target, "img_target": img_target,
                                "xml_target": xml_target}
                planned.append(planned_item)
                xml_groups.setdefault(target_dir, []).append(planned_item)

            for folder in xml_groups:
                xml_path = folder / "gamelist.xml"
                if xml_path.exists() or str(xml_path).casefold() in reserved:
                    raise FileExistsError(f"既存の gamelist.xml があるため中止します:\n{xml_path}")

        except Exception as exc:
            messagebox.showerror("事前確認エラー", f"{exc}\n\nファイルはコピーしていません。")
            return

        copied = []
        try:
            for entry in planned:
                target_dir = entry["target_dir"]
                (target_dir / "images").mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry["item"]["path"], entry["rom_target"])
                copied.append(entry["rom_target"])
                if entry["img_target"]:
                    shutil.copy2(entry["item"]["image"], entry["img_target"])
                    copied.append(entry["img_target"])

            for folder, entries in xml_groups.items():
                root_xml = ET.Element("gameList")
                for entry in entries:
                    item = entry["item"]
                    rom_target = entry["rom_target"]
                    img_target = entry["img_target"]
                    game = ET.SubElement(root_xml, "game")
                    xml_text(game, "gameid", rom_target.stem)
                    xml_text(game, "path", "./" + rom_target.name)
                    if img_target:
                        xml_text(game, "image", "./images/" + img_target.name)
                    xml_text(game, "video_id", "7")
                    xml_text(game, "class_type", "7")
                    xml_text(game, "game_type", "0")
                    xml_text(game, "timer", item["system"] or folder.name)
                    xml_text(game, "zh_CN", rom_target.stem)
                    xml_text(game, "en_US", rom_target.stem)
                    xml_text(game, "zh_TW", rom_target.stem)
                    xml_text(game, "ko_KR", rom_target.stem)
                    xml_text(game, "name", rom_target.stem)
                tree = ET.ElementTree(root_xml)
                ET.indent(tree, space="\t")
                xml_path = folder / "gamelist.xml"
                tree.write(xml_path, encoding="utf-8", xml_declaration=True)
                copied.append(xml_path)

            messagebox.showinfo("完了",
                f"処理が完了しました。\nROM: {len(planned)}件\n出力フォルダ: {len(xml_groups)}個")
            self.status_var.set(f"完了：ROM {len(planned)}件、出力フォルダ {len(xml_groups)}個")
        except Exception as exc:
            messagebox.showerror("処理エラー",
                f"処理中にエラーが発生しました。\n{exc}\n一部の出力ファイルが作成されている可能性があります。")
            self.status_var.set("エラーが発生しました。")

if __name__ == "__main__":
    App().mainloop()
