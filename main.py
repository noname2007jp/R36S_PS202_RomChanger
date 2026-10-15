from __future__ import annotations

import json
import os
import shutil
import ssl
import certifi
import urllib.parse
import urllib.request
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import xml.etree.ElementTree as ET

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
except ImportError:
    Image = ImageDraw = ImageFont = ImageOps = ImageTk = None


APP_TITLE = "R36S PS202 ROM Changer"
USER_AGENT = "R36S-PS202-RomChanger/0.1 (desktop utility)"


def https_context():
    """Use certifi's maintained CA bundle instead of a stale bundled/system CA list."""
    return ssl.create_default_context(cafile=certifi.where())


def next_backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.name}.bak_{stamp}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak_{stamp}_{counter}")
        counter += 1
    return candidate


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    destination = next_backup_path(path)
    shutil.copy2(path, destination)
    return destination


def safe_xml_path(base_dir: Path, raw_path: str) -> Path:
    raw = raw_path.strip().replace("\\", "/")
    if raw.startswith("./"):
        raw = raw[2:]
    p = Path(raw)
    return p.resolve() if p.is_absolute() else (base_dir / p).resolve()


def read_gamelist(folder: Path):
    xml_path = folder / "gamelist.xml"
    if not xml_path.is_file():
        return xml_path, []
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise RuntimeError(f"gamelist.xmlを読み込めませんでした: {exc}") from exc

    entries = []
    for game in root.findall(".//game"):
        path_node = game.find("path")
        image_node = game.find("image")
        name_node = game.find("name")
        if path_node is None or not path_node.text:
            continue
        entries.append({
            "rom": safe_xml_path(folder, path_node.text),
            "image": safe_xml_path(folder, image_node.text) if image_node is not None and image_node.text else None,
            "name": (name_node.text or "").strip() if name_node is not None else "",
        })
    return xml_path, entries


def find_xml_entry(entries, target: Path):
    target_resolved = target.resolve()
    for entry in entries:
        if entry["rom"] == target_resolved or entry["rom"].name.casefold() == target.name.casefold():
            return entry
    return None


def make_zip_from_source(source: Path, destination: Path):
    """Create a target-named ZIP; if source is a ZIP, copy its entries without extracting."""
    temp = destination.with_name(destination.name + ".tmp")
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as out_zip:
            if zipfile.is_zipfile(source):
                with zipfile.ZipFile(source, "r") as in_zip:
                    for info in in_zip.infolist():
                        if info.is_dir():
                            out_zip.writestr(info, b"")
                        else:
                            out_zip.writestr(info, in_zip.read(info.filename))
            else:
                out_zip.write(source, arcname=source.name)
        temp.replace(destination)
    finally:
        if temp.exists():
            temp.unlink()


def copy_rom(source: Path, target: Path):
    if source.resolve() == target.resolve():
        raise ValueError("入れ替え元と入れ替え先が同じファイルです。")
    if not source.is_file():
        raise FileNotFoundError(f"入れ替え元ROMが見つかりません: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.suffix.casefold() == ".zip":
        make_zip_from_source(source, target)
    elif zipfile.is_zipfile(source):
        # A non-ZIP destination expects a raw ROM file; don't silently extract an ambiguous archive.
        raise ValueError("入れ替え先がZIP以外ですが、入れ替え元はZIPです。入れ替え先も.zipにするか、ZIP内のROMを先に取り出してください。")
    else:
        shutil.copy2(source, target)


def load_font(size: int):
    candidates = [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\YuGothM.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def create_titled_thumbnail(source_image: Path, destination: Path, title: str, dimensions: tuple[int, int] | None):
    if Image is None:
        raise RuntimeError("Pillowがインストールされていません。py -m pip install -r requirements.txt を実行してください。")
    with Image.open(source_image) as original:
        img = ImageOps.exif_transpose(original).convert("RGB")
    if dimensions and dimensions[0] > 0 and dimensions[1] > 0:
        img = ImageOps.fit(img, dimensions, method=Image.Resampling.LANCZOS)
    else:
        img.thumbnail((400, 600), Image.Resampling.LANCZOS)

    if title.strip():
        draw = ImageDraw.Draw(img, "RGBA")
        pad = max(6, int(img.width * 0.035))
        font_size = max(12, int(img.width * 0.075))
        font = load_font(font_size)
        max_text_width = img.width - pad * 2
        text = title.strip()
        # Wrap the title to fit the thumbnail width.
        lines, current = [], ""
        for char in text:
            trial = current + char
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_text_width or not current:
                current = trial
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        line_height = max(font_size + 4, int(font_size * 1.25))
        max_lines = max(1, int((img.height * 0.32) / line_height))
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if lines:
                while lines[-1] and draw.textbbox((0, 0), lines[-1] + "…", font=font)[2] > max_text_width:
                    lines[-1] = lines[-1][:-1]
                lines[-1] = lines[-1] + "…"
        block_h = pad * 2 + line_height * len(lines)
        draw.rectangle((0, 0, img.width, min(img.height, block_h)), fill=(0, 0, 0, 190))
        y = pad
        for line in lines:
            draw.text((pad + 1, y + 1), line, font=font, fill=(0, 0, 0, 255), stroke_width=1)
            draw.text((pad, y), line, font=font, fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(20, 20, 20, 255))
            y += line_height

    destination.parent.mkdir(parents=True, exist_ok=True)
    fmt = "PNG" if destination.suffix.casefold() == ".png" else "JPEG"
    save_path = destination
    if fmt == "JPEG":
        img.save(save_path, format=fmt, quality=92, optimize=True)
    else:
        img.save(save_path, format=fmt, optimize=True)


def search_commons(query: str, limit: int = 8):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 360,
        "format": "json",
        "origin": "*",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15, context=https_context()) as response:
        data = json.loads(response.read().decode("utf-8"))
    pages = data.get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info_list = page.get("imageinfo") or []
        if not info_list:
            continue
        info = info_list[0]
        meta = info.get("extmetadata", {})
        license_name = meta.get("LicenseShortName", {}).get("value", "ライセンス情報なし")
        results.append({
            "title": page.get("title", ""),
            "url": info.get("thumburl") or info.get("url", ""),
            "source_url": info.get("descriptionurl", ""),
            "license": license_name,
        })
    return results


class RomChangerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x760")
        self.minsize(820, 650)
        self.folder_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.image_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.status_var = tk.StringVar(value="ROMフォルダーを選択してください。")
        self.search_var = tk.StringVar()
        self.candidates = []
        self.selected_candidate = None
        self.preview_photo = None
        self.xml_entries = []
        self.target_image_path = None
        self._build_ui()

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="R36S / PS202 ROM入れ替えツール", font=("", 16, "bold")).pack(anchor="w")
        ttk.Label(outer, text="gamelist.xmlは読み取り専用です。ROMと画像のみを更新します。").pack(anchor="w", pady=(2, 12))

        folder_frame = ttk.LabelFrame(outer, text="1. ROM設置場所", padding=8)
        folder_frame.pack(fill="x", pady=4)
        ttk.Entry(folder_frame, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(folder_frame, text="フォルダーを選択…", command=self.choose_folder).pack(side="right")

        files_frame = ttk.LabelFrame(outer, text="2. 入れ替え元／入れ替え先ROM", padding=8)
        files_frame.pack(fill="x", pady=4)
        ttk.Label(files_frame, text="入れ替えるROM（元）").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(files_frame, textvariable=self.source_var).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(files_frame, text="選択…", command=self.choose_source).grid(row=0, column=2, pady=4)
        ttk.Label(files_frame, text="入れ替え先ROM").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(files_frame, textvariable=self.target_var).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(files_frame, text="選択…", command=self.choose_target).grid(row=1, column=2, pady=4)
        files_frame.columnconfigure(1, weight=1)

        thumb_frame = ttk.LabelFrame(outer, text="3. サムネイル画像・表示タイトル", padding=8)
        thumb_frame.pack(fill="both", expand=True, pady=4)
        top = ttk.Frame(thumb_frame)
        top.pack(fill="x")
        ttk.Label(top, text="画像ファイル").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(top, textvariable=self.image_var).grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(top, text="ローカル画像…", command=self.choose_image).grid(row=0, column=2, pady=4)
        ttk.Label(top, text="画像に埋め込むタイトル").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(top, textvariable=self.title_var).grid(row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=4)
        top.columnconfigure(1, weight=1)

        searchrow = ttk.Frame(thumb_frame)
        searchrow.pack(fill="x", pady=(8, 4))
        ttk.Label(searchrow, text="Google画像検索").pack(side="left")
        ttk.Entry(searchrow, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(searchrow, text="ブラウザーで検索", command=self.open_google_images).pack(side="right")

        mid = ttk.Frame(thumb_frame)
        mid.pack(fill="both", expand=True, pady=4)
        self.candidate_list = tk.Listbox(mid, height=6, exportselection=False)
        self.candidate_list.pack_forget()
        self.preview_label = ttk.Label(mid, text="ローカル画像を選択するとプレビューを表示します", anchor="center")
        self.preview_label.pack(side="left", fill="both", expand=True, padx=10)
        self.candidate_info = ttk.Label(thumb_frame, text="Google画像検索で画像を保存し、「ローカル画像…」から選択してください。", wraplength=850)
        self.candidate_info.pack(fill="x", anchor="w", pady=4)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(10, 4))
        ttk.Button(buttons, text="入れ替え内容を確認", command=self.preview_operation).pack(side="left")
        ttk.Button(buttons, text="入れ替え実行", command=self.execute_operation).pack(side="right")
        ttk.Label(outer, textvariable=self.status_var, relief="sunken", anchor="w", padding=5).pack(fill="x", pady=(6, 0))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="ROMフォルダーを選択")
        if not folder:
            return
        self.folder_var.set(folder)
        try:
            xml_path, self.xml_entries = read_gamelist(Path(folder))
            if xml_path.exists():
                self.status_var.set(f"gamelist.xmlを読み取りました（{len(self.xml_entries)}件）。XMLは変更しません。")
            else:
                self.status_var.set("gamelist.xmlが見つかりません。ROMを選択できますが、サムネイルの自動特定はできません。")
        except Exception as exc:
            self.xml_entries = []
            messagebox.showerror("XML読み込みエラー", str(exc))

    def choose_source(self):
        initial = self.folder_var.get() or os.getcwd()
        path = filedialog.askopenfilename(title="入れ替えるROM（元）を選択", initialdir=initial,
                                          filetypes=[("ROM / ZIP", "*.zip *.gba *.gb *.gbc *.nes *.sfc *.smc *.iso *.bin *.cue *.chd"), ("すべてのファイル", "*.*")])
        if path:
            self.source_var.set(path)

    def choose_target(self):
        initial = self.folder_var.get() or os.getcwd()
        path = filedialog.askopenfilename(title="入れ替え先ROMを選択", initialdir=initial,
                                          filetypes=[("ROM / ZIP", "*.zip *.gba *.gb *.gbc *.nes *.sfc *.smc *.iso *.bin *.cue *.chd"), ("すべてのファイル", "*.*")])
        if path:
            self.target_var.set(path)
            self._autofill_from_target(Path(path))

    def _autofill_from_target(self, target: Path):
        folder = Path(self.folder_var.get()) if self.folder_var.get() else target.parent
        try:
            if folder != Path(self.folder_var.get()):
                _, self.xml_entries = read_gamelist(folder)
        except Exception:
            pass
        entry = find_xml_entry(self.xml_entries, target)
        if entry:
            self.title_var.set(entry["name"] or target.stem)
            self.target_image_path = entry["image"]
            if entry["image"]:
                self.image_var.set(str(entry["image"]))
                if entry["image"].is_file():
                    self.preview_local_image(entry["image"])
                self.status_var.set(f"XMLからサムネイル参照先を取得: {entry['image']}")
            else:
                self.image_var.set("")
                self.status_var.set("XMLエントリーにimageの指定がありません。")
        else:
            self.target_image_path = None
            self.title_var.set(target.stem)
            self.image_var.set("")
            self.status_var.set("対象ROMに一致するXMLエントリーがありません。画像保存先を手動選択してください。")

    def choose_image(self):
        path = filedialog.askopenfilename(title="サムネイル候補画像を選択",
                                          filetypes=[("画像", "*.png *.jpg *.jpeg *.webp *.bmp"), ("すべてのファイル", "*.*")])
        if path:
            self.image_var.set(path)
            self.selected_candidate = None
            self.preview_local_image(Path(path))
            self.status_var.set("ローカル画像を選択しました。入れ替え実行時にタイトルを埋め込みます。")

    def open_google_images(self):
        query = self.search_var.get().strip() or self.title_var.get().strip()
        if not query:
            messagebox.showinfo("Google画像検索", "検索語または表示タイトルを入力してください。")
            return
        url = "https://www.google.com/search?" + urllib.parse.urlencode({"udm": "2", "q": query})
        try:
            webbrowser.open(url)
            self.status_var.set("Google画像検索をブラウザーで開きました。画像を保存し、ローカル画像として選択してください。")
        except Exception as exc:
            messagebox.showerror("Google画像検索", f"ブラウザーを開けませんでした。\\n{exc}")

    def preview_local_image(self, path: Path):
        if Image is None:
            self.preview_label.configure(image="", text="Pillowが未インストールです")
            return
        try:
            with Image.open(path) as img:
                preview = ImageOps.exif_transpose(img).convert("RGB")
                preview.thumbnail((300, 360), Image.Resampling.LANCZOS)
                self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview_photo, text="")
            self.candidate_info.config(text=f"選択画像: {path}")
        except Exception as exc:
            self.preview_label.configure(image="", text="プレビューを取得できません")
            self.status_var.set(f"プレビュー取得エラー: {exc}")

    def search_images(self):
        query = self.search_var.get().strip() or self.title_var.get().strip()
        if not query:
            messagebox.showinfo("画像検索", "検索語または表示タイトルを入力してください。")
            return
        self.status_var.set("Wikimedia Commonsを検索しています…")
        self.update_idletasks()
        try:
            self.candidates = search_commons(query)
        except Exception as exc:
            messagebox.showerror("画像検索エラー", f"画像候補を取得できませんでした。\n{exc}")
            self.status_var.set("画像検索に失敗しました。")
            return
        self.candidate_list.delete(0, tk.END)
        for item in self.candidates:
            self.candidate_list.insert(tk.END, item["title"])
        self.candidate_info.config(text=f"{len(self.candidates)}件の候補。候補を選択して出典・ライセンスを確認してください。")
        self.status_var.set(f"画像候補を{len(self.candidates)}件取得しました。")
        if self.candidates:
            self.candidate_list.selection_set(0)
            self.on_candidate_select()

    def on_candidate_select(self, _event=None):
        selected = self.candidate_list.curselection()
        if not selected:
            return
        item = self.candidates[selected[0]]
        self.selected_candidate = item
        self.candidate_info.config(text=f"ライセンス: {item['license']} | 出典: {item['source_url']}")
        try:
            req = urllib.request.Request(item["url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read()
            import io
            with Image.open(io.BytesIO(raw)) as img:
                preview = img.convert("RGB")
                preview.thumbnail((220, 280), Image.Resampling.LANCZOS)
                self.preview_photo = ImageTk.PhotoImage(preview)
            self.preview_label.configure(image=self.preview_photo, text="")
            # Download is deferred until execution; remember URL and source metadata.
            self.image_var.set(item["url"])
            self.status_var.set("ネット画像候補を選択しました。実行時にダウンロードして加工します。")
        except Exception as exc:
            self.preview_label.configure(image="", text="プレビューを取得できません")
            self.status_var.set(f"プレビュー取得エラー: {exc}")

    def _get_selected_image(self) -> Path:
        raw = self.image_var.get().strip()
        if not raw:
            raise ValueError("サムネイル画像を選択するか、ネット画像候補を選んでください。")
        if raw.startswith("https://") or raw.startswith("http://"):
            import tempfile
            suffix = Path(urllib.parse.urlparse(raw).path).suffix
            if suffix.casefold() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                suffix = ".img"
            fd, name = tempfile.mkstemp(prefix="ps202_thumbnail_", suffix=suffix)
            os.close(fd)
            req = urllib.request.Request(raw, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=30, context=https_context()) as response, open(name, "wb") as out:
                    shutil.copyfileobj(response, out)
            except Exception:
                Path(name).unlink(missing_ok=True)
                raise
            return Path(name)
        path = Path(raw)
        if not path.is_file():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {path}")
        return path

    def _resolve_image_target(self, target_rom: Path) -> Path:
        if self.target_image_path:
            return self.target_image_path
        # If XML has no matching image, let the user choose an output path.
        path = filedialog.asksaveasfilename(title="サムネイル保存先を指定",
                                            initialdir=str(target_rom.parent),
                                            initialfile=target_rom.stem + ".png",
                                            defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])
        if not path:
            raise ValueError("サムネイル保存先が指定されていません。")
        return Path(path)

    def preview_operation(self):
        try:
            source = Path(self.source_var.get())
            target = Path(self.target_var.get())
            if not source.is_file() or not target.is_file():
                raise ValueError("入れ替え元ROMと入れ替え先ROMを選択してください。")
            img_target = self._resolve_image_target(target)
            title = self.title_var.get().strip() or target.stem
            details = (
                f"元ROM: {source}\n"
                f"入れ替え先: {target}\n"
                f"入れ替え先のバックアップ: {target.name}.bak_日時\n"
                f"サムネイル保存先: {img_target}\n"
                f"画像タイトル: {title}\n\n"
                "gamelist.xmlは変更しません。実行しますか？"
            )
            if messagebox.askyesno("入れ替え内容の確認", details):
                self.execute_operation()
        except Exception as exc:
            messagebox.showerror("確認できません", str(exc))

    def execute_operation(self):
        temp_image = None
        try:
            if Image is None:
                raise RuntimeError("Pillowが未インストールです。py -m pip install -r requirements.txt を実行してください。")
            source = Path(self.source_var.get()).resolve()
            target = Path(self.target_var.get()).resolve()
            if not source.is_file() or not target.is_file():
                raise ValueError("入れ替え元ROMと入れ替え先ROMを選択してください。")
            if source == target:
                raise ValueError("入れ替え元と入れ替え先が同じファイルです。")

            img_target = self._resolve_image_target(target).resolve()
            if not img_target.parent.exists():
                raise FileNotFoundError(f"サムネイル保存フォルダーが存在しません: {img_target.parent}")
            title = self.title_var.get().strip() or target.stem
            selected_image = self._get_selected_image()
            if selected_image.name.startswith("ps202_thumbnail_"):
                temp_image = selected_image

            dimensions = None
            if img_target.is_file():
                with Image.open(img_target) as existing:
                    dimensions = existing.size
            elif self.target_image_path and self.target_image_path.is_file():
                with Image.open(self.target_image_path) as existing:
                    dimensions = existing.size

            # Prepare thumbnail first; if image processing fails, don't alter the ROM.
            staged_image = img_target.with_name(img_target.stem + ".new" + img_target.suffix)
            create_titled_thumbnail(selected_image, staged_image, title, dimensions)

            rom_backup = backup_file(target)
            image_backup = backup_file(img_target)
            try:
                copy_rom(source, target)
                staged_image.replace(img_target)
            except Exception:
                if target.exists() and rom_backup:
                    shutil.copy2(rom_backup, target)
                if image_backup and image_backup.exists():
                    shutil.copy2(image_backup, img_target)
                raise
            finally:
                staged_image.unlink(missing_ok=True)

            message = "入れ替えが完了しました。\n\n"
            message += f"ROM: {target}\n"
            message += f"ROMバックアップ: {rom_backup or '既存ファイルなし'}\n"
            message += f"サムネイル: {img_target}\n"
            message += f"画像バックアップ: {image_backup or '既存ファイルなし'}\n"
            message += "\ngamelist.xmlは変更していません。"
            messagebox.showinfo("完了", message)
            self.status_var.set("入れ替え完了。ROM・サムネイルのバックアップを作成しました。")
        except Exception as exc:
            messagebox.showerror("入れ替えエラー", str(exc))
            self.status_var.set(f"エラー: {exc}")
        finally:
            if temp_image:
                temp_image.unlink(missing_ok=True)


if __name__ == "__main__":
    app = RomChangerApp()
    app.mainloop()
