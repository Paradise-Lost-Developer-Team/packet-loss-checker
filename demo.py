"""
VALORANT パケットロス追跡ツール - デモ用データ生成スクリプト
実際のテストを行わずに、サンプルデータで機能をテストできます。
"""

import random
import json
from datetime import datetime, timedelta
from rich.console import Console

from main import VALORANTServerTracker, PingResult
from font_utils import setup_matplotlib_japanese

console = Console()

# 日本語フォント設定
setup_matplotlib_japanese()

def generate_demo_data(duration_minutes: int = 10, region: str = "Tokyo (Japan)") -> list:
    """デモ用のパケットロスデータを生成"""
    tracker = VALORANTServerTracker()
    results = []
    
    if region not in tracker.VALORANT_SERVERS:
        console.print(f"[red]❌ 無効なリージョン: {region}[/red]")
        return []
    
    servers = tracker.VALORANT_SERVERS[region]
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    
    # 時間経過をシミュレート
    for minute in range(duration_minutes * 60):  # 秒単位でデータ生成
        timestamp = start_time + timedelta(seconds=minute)
        
        for server in servers:
            # リアルなレイテンシーとパケットロスを生成
            base_latency = random.uniform(15, 35)  # 東京サーバーの基本レイテンシー
            
            # 時々発生するネットワーク問題をシミュレート
            if random.random() < 0.02:  # 2%の確率でパケットロス
                result = PingResult(
                    timestamp=timestamp.isoformat(),
                    server=server,
                    latency=None,
                    packet_loss=True,
                    timeout=True
                )
            elif random.random() < 0.05:  # 5%の確率で高レイテンシー
                high_latency = base_latency + random.uniform(50, 200)
                result = PingResult(
                    timestamp=timestamp.isoformat(),
                    server=server,
                    latency=high_latency,
                    packet_loss=False,
                    timeout=False
                )
            else:
                # 通常のレイテンシー（ジッターを含む）
                jitter = random.uniform(-5, 5)
                normal_latency = base_latency + jitter
                result = PingResult(
                    timestamp=timestamp.isoformat(),
                    server=server,
                    latency=max(1, normal_latency),  # 最小1ms
                    packet_loss=False,
                    timeout=False
                )
            
            results.append(result)
    
    return results

def run_demo():
    """デモンストレーション実行"""
    console.print("[bold green]🎮 VALORANT パケットロス追跡ツール - デモモード[/bold green]")
    console.print("=" * 60)
    
    # デモデータ生成（進捗表示付き）
    console.print("📊 デモデータを生成中...")
    console.print("[dim]データ生成には数秒かかります...[/dim]")
    
    # プログレスバーシミュレーション
    import time
    for i in range(5):
        progress = (i + 1) * 20
        bar = "█" * (progress // 5) + "░" * (20 - progress // 5)
        console.print(f"\r[{bar}] {progress}%", end="")
        time.sleep(0.5)
    console.print("\n")
    
    demo_results = generate_demo_data(duration_minutes=10, region="Tokyo (Japan)")
    
    # 一般サービスのデモデータも生成
    console.print("🌐 一般サービスのデモデータを生成中...")
    reference_demo_data = generate_reference_demo_data(duration_minutes=5)
    
    # トラッカーにデモデータを設定
    tracker = VALORANTServerTracker()
    tracker.results = demo_results
    tracker.reference_results = reference_demo_data
    tracker.current_region = "Tokyo (Japan)"
    tracker.start_time = datetime.now() - timedelta(minutes=10)
    
    console.print(f"✅ {len(demo_results)}個のVALORANTテストデータを生成しました")
    console.print(f"✅ {len(reference_demo_data)}個の一般サービステストデータを生成しました")
    console.print("\n📈 結果を表示します...")
    
    # 結果表示
    tracker.display_results()
    
    # 比較分析
    console.print("\n🔍 問題の原因を分析します...")
    tracker.display_comparison_results()
    
    # ファイル保存のデモ
    console.print("\n💾 デモ結果を保存中...")
    tracker.save_results("demo_test")
    
    # グラフ作成のデモ
    console.print("\n📊 グラフを作成中...")
    tracker.create_visualization("demo_analysis")
    
    console.print("\n🎉 デモが完了しました！")
    console.print("生成されたファイルを確認してください：")
    console.print("- demo_test.csv (詳細データ)")
    console.print("- demo_test_stats.json (統計情報)")
    console.print("- demo_analysis.png (グラフ)")
    console.print("\n💡 実際のテストを行うには 'python main.py' を実行してください")
    console.print("[yellow]💡 実際のテストでは残り時間とプログレスバーが表示されます[/yellow]")

def generate_reference_demo_data(duration_minutes: int = 5) -> list:
    """一般サービス用のデモデータを生成"""
    results = []
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    
    # 各サービスから1つずつサーバーを選択
    reference_servers = {
        "Discord": "162.159.130.232",
        "YouTube (Google)": "8.8.8.8", 
        "Cloudflare": "1.1.1.1",
        "Amazon (AWS)": "52.95.110.1"
    }
    
    for minute in range(duration_minutes * 60):
        timestamp = start_time + timedelta(seconds=minute)
        
        for service, server in reference_servers.items():
            # 一般サービスは比較的安定
            base_latency = random.uniform(10, 25)
            
            # 稀にパケットロス（0.5%の確率）
            if random.random() < 0.005:
                result = PingResult(
                    timestamp=timestamp.isoformat(),
                    server=f"{service}|{server}",
                    latency=None,
                    packet_loss=True,
                    timeout=True
                )
            else:
                # 通常のレイテンシー
                jitter = random.uniform(-3, 3)
                normal_latency = base_latency + jitter
                result = PingResult(
                    timestamp=timestamp.isoformat(),
                    server=f"{service}|{server}",
                    latency=max(1, normal_latency),
                    packet_loss=False,
                    timeout=False
                )
            
            results.append(result)
    
    return results

if __name__ == "__main__":
    run_demo()
