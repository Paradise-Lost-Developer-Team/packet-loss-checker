# 🚀 文字化け修正ガイド

## 問題

チャートや統計グラフで日本語文字が □ や ? として表示される文字化けが発生する場合があります。

## 原因

システムに適切な日本語フォントがインストールされていない、またはmatplotlibが日本語フォントを認識できていないことが原因です。

## 自動修正

このツールには自動的に日本語フォントを検出・設定する機能が組み込まれています：

```python
from font_utils import setup_matplotlib_japanese
setup_matplotlib_japanese()
```

## 対応フォント

### Windows

- Yu Gothic ✅ (推奨)
- Yu Gothic UI
- Meiryo
- MS Gothic
- MS PGothic

### macOS

- Hiragino Sans ✅ (推奨)
- Hiragino Kaku Gothic Pro
- Hiragino Maru Gothic Pro
- Osaka

### Linux

- Noto Sans CJK JP ✅ (推奨)
- IPAexGothic
- IPAGothic
- TakaoGothic
- VL Gothic

## 手動インストール

### Windows での Noto Sans フォントインストール

1. [Google Fonts - Noto Sans JP](https://fonts.google.com/noto/specimen/Noto+Sans+JP) にアクセス
2. 「Download family」をクリック
3. ダウンロードしたZIPファイルを解凍
4. `.ttf` ファイルを右クリック → 「インストール」
5. プログラムを再起動

### macOS での Noto Sans フォントインストール

1. Font Book アプリケーションを開く
2. [Google Fonts - Noto Sans JP](https://fonts.google.com/noto/specimen/Noto+Sans+JP) からフォントをダウンロード
3. ダウンロードしたフォントファイルをFont Bookにドラッグ＆ドロップ
4. プログラムを再起動

### Linux での日本語フォントインストール

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install fonts-noto-cjk
```

#### CentOS/RHEL

```bash
sudo yum install google-noto-sans-cjk-jp-fonts
```

#### Arch Linux

```bash
sudo pacman -S noto-fonts-cjk
```

## 確認方法

フォントが正しく設定されているかテストするには：

```bash
python font_utils.py
```

または：

```bash
python -c "from font_utils import setup_matplotlib_japanese; setup_matplotlib_japanese()"
```

成功時の出力例：

✅ 日本語フォントを設定しました: Yu Gothic

## トラブルシューティング

### 問題1: 「日本語フォントが見つかりません」というメッセージ

**解決策:**

1. 上記の手動インストール手順に従ってフォントをインストール
2. プログラムを再起動
3. 再度テストを実行

### 問題2: グラフで一部の文字のみ文字化け

**解決策:**

1. matplotlib のフォントキャッシュをクリア：
2. プログラムを再起動

```python
import matplotlib.font_manager as fm
fm._rebuild()

```

### 問題3: エラーメッセージが表示される

**解決策:**

1. 依存関係を再インストール：
2. プログラムを再起動

```bash
pip install --upgrade matplotlib
```

## サポートされる表示

修正後は以下の日本語テキストが正しく表示されます：

- グラフタイトル: 「VALORANT パケットロス解析」
- 軸ラベル: 「レイテンシー (ms)」「パケットロス率 (%)」
- 凡例: 「平均レイテンシー」「ジッター」
- 統計テーブル: 日本語カラムヘッダー
- 分析結果: 日本語の推奨事項

## 注意事項

- フォント設定の変更後は、必ずプログラムを再起動してください
- 一部の環境では、システムのロケール設定も影響する場合があります
- カスタムフォントを使用したい場合は、`font_utils.py` の設定を変更してください
