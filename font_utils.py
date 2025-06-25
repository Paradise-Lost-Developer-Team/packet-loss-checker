"""
フォント設定ユーティリティ
日本語フォントの自動検出と設定を行う
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os
from pathlib import Path

def find_japanese_fonts():
    """システムで利用可能な日本語フォントを検索"""
    # システム別のフォント候補
    font_candidates = {
        'Windows': [
            'Yu Gothic',
            'Yu Gothic UI', 
            'Meiryo',
            'MS Gothic',
            'MS PGothic',
            'Noto Sans CJK JP'
        ],
        'Darwin': [  # macOS
            'Hiragino Sans',
            'Hiragino Kaku Gothic Pro',
            'Hiragino Maru Gothic Pro',
            'Noto Sans CJK JP',
            'Osaka'
        ],
        'Linux': [
            'Noto Sans CJK JP',
            'IPAexGothic',
            'IPAGothic',
            'TakaoGothic',
            'VL Gothic',
            'Sazanami Gothic'
        ]
    }
    
    system = platform.system()
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # システム固有のフォントを優先して検索
    if system in font_candidates:
        for font in font_candidates[system]:
            if font in available_fonts:
                return font
    
    # 全プラットフォーム共通フォントを検索
    universal_fonts = ['Noto Sans CJK JP', 'DejaVu Sans']
    for font in universal_fonts:
        if font in available_fonts:
            return font
    
    return None

def setup_matplotlib_japanese():
    """matplotlibの日本語フォント設定"""
    try:
        # 日本語フォントを検索
        japanese_font = find_japanese_fonts()
        
        if japanese_font:
            plt.rcParams['font.family'] = japanese_font
            plt.rcParams['font.size'] = 10
            print(f"✅ 日本語フォントを設定しました: {japanese_font}")
        else:
            # フォールバック設定
            plt.rcParams['font.family'] = 'DejaVu Sans'
            plt.rcParams['font.size'] = 10
            print("⚠️ 日本語フォントが見つかりません。英語表記になる場合があります。")
        
        # 負の符号（マイナス記号）の文字化けを防ぐ
        plt.rcParams['axes.unicode_minus'] = False
        
        return True
        
    except Exception as e:
        print(f"❌ フォント設定でエラーが発生しました: {e}")
        # 安全なフォールバック
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        return False

def install_japanese_font_instructions():
    """日本語フォントのインストール方法を表示"""
    system = platform.system()
    
    instructions = {
        'Windows': """
Windows で日本語フォントをインストールするには:
1. Noto Sans CJK JP をダウンロード: https://fonts.google.com/noto/specimen/Noto+Sans+JP
2. ダウンロードしたフォントファイルを右クリック → 「インストール」
3. プログラムを再起動
        """,
        'Darwin': """
macOS で日本語フォントをインストールするには:
1. Font Book アプリケーションを開く
2. Noto Sans CJK JP をダウンロード: https://fonts.google.com/noto/specimen/Noto+Sans+JP
3. ダウンロードしたフォントをFont Bookにドラッグ＆ドロップ
4. プログラムを再起動
        """,
        'Linux': """
Linux で日本語フォントをインストールするには:
Ubuntu/Debian:
  sudo apt-get install fonts-noto-cjk

CentOS/RHEL:
  sudo yum install google-noto-sans-cjk-jp-fonts

Arch Linux:
  sudo pacman -S noto-fonts-cjk

インストール後、プログラムを再起動してください。
        """
    }
    
    if system in instructions:
        print(instructions[system])
    else:
        print("お使いのシステム用の日本語フォントインストール方法については、")
        print("https://fonts.google.com/noto/specimen/Noto+Sans+JP を参照してください。")

if __name__ == "__main__":
    # フォント設定のテスト
    success = setup_matplotlib_japanese()
    if not success:
        install_japanese_font_instructions()
