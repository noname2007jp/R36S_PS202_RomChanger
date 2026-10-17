# R36S PS202 ROM Changer

Windows向けのPS202 ROM入れ替え・サムネイル編集ツール、およびROM・画像の一括コピー／gamelist.xml生成ツールです。

## ROM・画像関連付けツール（新機能）

- Windows用の単体EXEをGitHub Actionsでビルドします（インストール不要）。
- ROM保存元フォルダとコピー先の `roms` フォルダを指定します。
- ROMファイルを一覧表示し、各ROMの行から対応画像を個別に選択できます。
- ROMのファイル名を基準に画像をリネームして、各システムの `images` フォルダへコピーします。
- システム別フォルダと `gamelist.xml` を生成します。
- 既存のROM、画像、gamelist.xmlがあれば上書きせず中止します。
- 元ファイルは変更・削除しません。

### EXEの取得方法

1. GitHubの **Actions** タブを開きます。
2. **Build Windows EXE** ワークフローを選択します。
3. 成功した実行を開き、Artifacts の `PS202_ROM_Gamelist_Builder-Windows` をダウンロードします。
4. ZIPを展開し、`PS202_ROM_Gamelist_Builder.exe` を実行します。

## 既存ROM Changer

従来のROM入れ替え・サムネイル編集ツールの説明やファイルは維持します。

## 注意

- 実機用のXMLタグ値は提供されたサンプルをもとに設定しています。実機での動作確認は必須です。
- 初回は本番SDカードではなく、バックアップまたはテスト用フォルダで生成結果を確認してください。
- 既存の `gamelist.xml` が存在するシステムフォルダでは上書きせず停止します。既存XMLへの追記／統合は今後の拡張対象です。
