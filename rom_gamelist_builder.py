from __future__ import annotations

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime

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
    ".n64", ".z64", ".v64", ".rom", ".img", ".pbp",
}

def xml_text(parent, tag, value):
    child = ET.SubElement(parent, tag)
    child.text = str(value)
    return child

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PS202 ROM・画像関連付けツール")
        self.geometry("1080x700")
        self.minsize(850, 560)
        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.status_var = tk.StringVar(value="ROMフォルダを選択してください。")
        self.items = []
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="ROM保存元フォルダ").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(top, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="参照...", command=self.choose_source).grid(row=0, column=2)
        ttk.Label(top, text="コピー先の roms フォルダ").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(top, textvariable=self.dest_var).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="参照...", command=self.choose_dest).grid(row=1, column=2)
        top.columnconfigure(1, weight=1)

        actions = ttk.Frame(self, padding=(10, 0, 10, 8))
        actions.pack(fill="x")
        ttk.Button(actions, text="ROM一覧を読み込む", command=self.load_roms).pack(side="left")
        ttk.Label(actions, text="各ROMの行でシステムと画像を指定してください。").pack(side="left", padx=12)

        columns = ("rom", "system", "image", "output")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("rom", text="ROMファイル")
        self.tree.heading("system", text="システムフォルダ")
        self.tree.heading("image", text="関連付け画像")
        self.tree.heading("output", text="画像の出力名")
        self.tree.column("rom", width=300, anchor="w")
        self.tree.column("system", width=130, anchor="center")
        self.tree.column("image", width=300, anchor="w")
        self.tree.column("output", width=250, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10)
        self.tree.bind("<Double-1>", self.on_double_click)

        controls = ttk.Frame(self, padding=10)
        controls.pack(fill="x")
        ttk.Button(controls, text="選択ROMのシステム変更", command=self.change_system).pack(side="left")
        ttk.Button(controls, text="選択ROMの画像選択", command=self.choose_image).pack(side="left", padx=6)
        ttk.Button(controls, text="画像を解除", command=self.clear_image).pack(side="left")
        ttk.Button(controls, text="生成・コピーを実行", command=self.execute).pack(side="right")

        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=5).pack(fill="x", side="bottom")

    def choose_source(self):
        p = filedialog.askdirectory(title="ROM保存元フォルダを選択")
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
        files = sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in ROM_EXTS)
        for p in files:
            system = EXT_SYSTEM.get(p.suffix.lower(), "")
            item = {"path": p, "system": system, "image": None}
            self.items.append(item)
            self._insert(item)
        self.status_var.set(f"{len(self.items)}件のROMを読み込みました。")
        if not files:
            messagebox.showinfo("ROMなし", "対応する拡張子のROMが見つかりませんでした。")

    def _insert(self, item):
        p = item["path"]
        image = item["image"]
        output = p.stem + image.suffix.lower() if image else ""
        self.tree.insert("", "end", iid=str(len(self.tree.get_children())), values=(
            p.name, item["system"] or "未指定", str(image) if image else "（未指定）", output
        ))

    def _selected_index(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("選択", "一覧からROMを選択してください。")
            return None
        return int(selected[0])

    def _refresh_row(self, index):
        children = self.tree.get_children()
        if index >= len(children):
            return
        item = self.items[index]
        p, image = item["path"], item["image"]
        self.tree.item(children[index], values=(
            p.name, item["system"] or "未指定", str(image) if image else "（未指定）",
            p.stem + image.suffix.lower() if image else ""
        ))

    def choose_image(self):
        i = self._selected_index()
        if i is None:
            return
        p = filedialog.askopenfilename(
            title=f"{self.items[i]['path'].name} に対応する画像を選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.bmp *.webp"), ("すべてのファイル", "*.*")]
        )
        if p:
            self.items[i]["image"] = Path(p)
            self._refresh_row(i)

    def clear_image(self):
        i = self._selected_index()
        if i is not None:
            self.items[i]["image"] = None
            self._refresh_row(i)

    def change_system(self):
        i = self._selected_index()
        if i is None:
            return
        dialog = tk.Toplevel(self)
        dialog.title("システムフォルダを選択")
        dialog.transient(self)
        dialog.grab_set()
        var = tk.StringVar(value=self.items[i]["system"] or SYSTEMS[0])
        ttk.Label(dialog, text="コピー先のシステムフォルダ").pack(padx=16, pady=(16, 4))
        combo = ttk.Combobox(dialog, textvariable=var, values=SYSTEMS, state="readonly", width=24)
        combo.pack(padx=16, pady=4)
        def save():
            self.items[i]["system"] = var.get()
            self._refresh_row(i)
            dialog.destroy()
        ttk.Button(dialog, text="決定", command=save).pack(pady=12)

    def on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        col = self.tree.identify_column(event.x)
        if region == "cell" and col == "#3":
            self.choose_image()
        elif region == "cell" and col == "#2":
            self.change_system()

    def execute(self):
        dest = Path(self.dest_var.get().strip().strip('"'))
        if not self.items:
            messagebox.showerror("実行できません", "先にROM一覧を読み込んでください。")
            return
        if not dest.is_dir():
            messagebox.showerror("入力エラー", "有効なコピー先の roms フォルダを指定してください。")
            return
        missing = [x["path"].name for x in self.items if not x["system"]]
        if missing:
            messagebox.showerror("システム未指定", "システムフォルダが未指定のROMがあります。\n" + "\n".join(missing[:20]))
            return
        if not messagebox.askyesno("最終確認", f"{len(self.items)}件のROMをコピーし、システム別 gamelist.xml を生成します。\n既存ファイルは上書きせず、衝突時は中止します。\n続行しますか？"):
            return

        # Validate every destination before writing anything.
        planned = []
        for item in self.items:
            sysdir = dest / item["system"]
            rom_target = sysdir / item["path"].name
            img_target = (sysdir / "images" / (item["path"].stem + item["image"].suffix.lower())) if item["image"] else None
            xml_target = sysdir / "gamelist.xml"
            for target in (rom_target, img_target):
                if target and target.exists():
                    messagebox.showerror("上書き防止", f"既存ファイルがあるため処理を中止しました。\n{target}\n既存ファイルは変更していません。")
                    return
            planned.append((item, sysdir, rom_target, img_target, xml_target))

        # Existing gamelist files are never overwritten.
        systems = {x["system"] for x in self.items}
        for system in systems:
            xml_path = dest / system / "gamelist.xml"
            if xml_path.exists():
                messagebox.showerror("上書き防止", f"既存の gamelist.xml があるため処理を中止しました。\n{xml_path}\n既存XMLを保護するため、事前に退避または別フォルダを指定してください。")
                return

        try:
            for item, sysdir, rom_target, img_target, _ in planned:
                (sysdir / "images").mkdir(parents=True, exist_ok=True)
                shutil.copy2(item["path"], rom_target)
                if item["image"] and img_target:
                    shutil.copy2(item["image"], img_target)

            for system in systems:
                root = ET.Element("gameList")
                for item, sysdir, rom_target, img_target, _ in planned:
                    if item["system"] != system:
                        continue
                    game = ET.SubElement(root, "game")
                    # IDs are unique within the generated XML; device-specific values follow the supplied sample.
                    xml_text(game, "gameid", str(rom_target.stem))
                    xml_text(game, "path", "./" + rom_target.name)
                    if img_target:
                        xml_text(game, "image", "./images/" + img_target.name)
                    xml_text(game, "video_id", "7")
                    xml_text(game, "class_type", "7")
                    xml_text(game, "game_type", "0")
                    xml_text(game, "timer", system)
                    xml_text(game, "zh_CN", rom_target.stem)
                    xml_text(game, "en_US", rom_target.stem)
                    xml_text(game, "zh_TW", rom_target.stem)
                    xml_text(game, "ko_KR", rom_target.stem)
                    xml_text(game, "name", rom_target.stem)
                tree = ET.ElementTree(root)
                ET.indent(tree, space="\t")
                xml_path = dest / system / "gamelist.xml"
                tree.write(xml_path, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("完了", f"処理が完了しました。\nROM: {len(planned)}件\nシステム: {len(systems)}種類")
            self.status_var.set(f"完了：ROM {len(planned)}件、システム {len(systems)}種類")
        except Exception as exc:
            messagebox.showerror("処理エラー", f"処理中にエラーが発生しました。\n{exc}\n部分的に作成されたファイルがある場合は確認してください。")
            self.status_var.set("エラーが発生しました。")

if __name__ == "__main__":
    App().mainloop()
