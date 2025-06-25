#!/usr/bin/env python3
"""
VALORANT パケットロス追跡ツール - クイックテスト
残り時間表示のテスト用
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

import ping3
from rich.console import Console
from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.live import Live
from rich import box
from colorama import init, Fore, Style

# カラー初期化
init(autoreset=True)
console = Console()

@dataclass
class PingResult:
    """Pingテストの結果を格納するクラス"""
    timestamp: str
    server: str
    latency: Optional[float]
    packet_loss: bool
    timeout: bool

class QuickTester:
    """残り時間表示のクイックテスト用クラス"""
    
    # テスト用サーバー（応答の早いもの）
    TEST_SERVERS = ["8.8.8.8", "1.1.1.1"]  # Google DNS, Cloudflare
    
    def __init__(self, timeout: float = 2.0, interval: float = 0.5):
        self.timeout = timeout
        self.interval = interval
        self.results: List[PingResult] = []
        self.is_running = False
        self.start_time = None
        
    def ping_server(self, server: str) -> PingResult:
        """サーバーにpingを送信"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            latency = ping3.ping(server, timeout=self.timeout)
            if latency is None:
                return PingResult(timestamp, server, None, True, True)
            else:
                latency_ms = latency * 1000  # 秒をミリ秒に変換
                return PingResult(timestamp, server, latency_ms, False, False)
        except Exception:
            return PingResult(timestamp, server, None, True, True)
    
    def run_quick_test(self, duration_seconds: int = 30):
        """短時間のテストを実行（残り時間表示付き）"""
        console.print(Panel.fit(
            "🚀 残り時間表示テスト",
            style="bold blue"
        ))
        
        servers = self.TEST_SERVERS
        self.is_running = True
        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(seconds=duration_seconds)
        
        console.print(f"[green]📍 テスト期間: {duration_seconds}秒[/green]")
        console.print(f"[blue]🕐 開始時刻: {self.start_time.strftime('%H:%M:%S')}[/blue]")
        console.print(f"[blue]🏁 終了予定時刻: {end_time.strftime('%H:%M:%S')}[/blue]")
        console.print()
        
        try:
            while self.is_running and datetime.now() < end_time:
                current_time = datetime.now()
                
                # 残り時間計算
                remaining_time = end_time - current_time
                remaining_minutes = int(remaining_time.total_seconds() // 60)
                remaining_seconds = int(remaining_time.total_seconds() % 60)
                
                # 進捗計算
                elapsed_time = current_time - self.start_time
                progress_percentage = min(100, (elapsed_time.total_seconds() / duration_seconds) * 100)
                
                for server in servers:
                    if not self.is_running:
                        break
                        
                    result = self.ping_server(server)
                    self.results.append(result)
                    
                    # リアルタイム結果表示（改善された時間表示付き）
                    status = "❌ LOSS" if result.packet_loss else f"✅ {result.latency:.1f}ms"
                    progress_bar = "█" * int(progress_percentage // 5) + "░" * (20 - int(progress_percentage // 5))
                    
                    # より詳細な時間表示
                    elapsed_minutes = int(elapsed_time.total_seconds() // 60)
                    elapsed_seconds_remainder = int(elapsed_time.total_seconds() % 60)
                    time_info = f"⏱️ {elapsed_minutes:02d}:{elapsed_seconds_remainder:02d} / {remaining_minutes:02d}:{remaining_seconds:02d}"
                    
                    console.print(
                        f"[dim]{result.timestamp[-8:]}[/dim] {server}: {status} "
                        f"[cyan]│[/cyan] [{progress_bar}] {progress_percentage:.1f}% "
                        f"[yellow]{time_info}[/yellow]"
                    )
                    
                    # リアルタイム統計表示（10秒ごと）
                    if int(elapsed_time.total_seconds()) % 10 == 0 and elapsed_time.total_seconds() > 0:
                        self._show_quick_stats()
                    
                    time.sleep(self.interval)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ テストが中断されました[/yellow]")
        finally:
            self.is_running = False
            elapsed_time = datetime.now() - self.start_time
            console.print(f"\n[green]✅ テストが完了しました（実行時間: {elapsed_time.total_seconds():.0f}秒）[/green]")
            
        # 簡単な統計表示
        if self.results:
            successful_pings = [r for r in self.results if not r.packet_loss]
            lost_packets = len([r for r in self.results if r.packet_loss])
            total_packets = len(self.results)
            packet_loss_rate = (lost_packets / total_packets) * 100 if total_packets > 0 else 0
            
            console.print(f"\n[cyan]📊 テスト結果:[/cyan]")
            console.print(f"   総パケット: {total_packets}")
            console.print(f"   パケットロス: {lost_packets} ({packet_loss_rate:.1f}%)")
            
            if successful_pings:
                latencies = [r.latency for r in successful_pings]
                avg_latency = statistics.mean(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                
                console.print(f"   平均レイテンシー: {avg_latency:.1f}ms")
                console.print(f"   最小/最大: {min_latency:.1f}/{max_latency:.1f}ms")
                
    def _show_quick_stats(self):
        """クイック統計表示"""
        if len(self.results) < 5:
            return
            
        recent_results = self.results[-10:]  # 最新の10件
        lost_packets = len([r for r in recent_results if r.packet_loss])
        successful_pings = [r for r in recent_results if not r.packet_loss]
        
        if recent_results:
            loss_rate = (lost_packets / len(recent_results)) * 100
            avg_latency = statistics.mean([r.latency for r in successful_pings]) if successful_pings else 0
            
            console.print(f"[dim]    📊 直近10件: ロス {loss_rate:.0f}% | 平均 {avg_latency:.1f}ms[/dim]")

def main():
    """メイン関数"""
    console.print(Panel.fit(
        "🎮 残り時間表示テスト\n高速ネットワークテスト",
        style="bold green"
    ))
    
    tester = QuickTester()
    
    # 30秒のクイックテスト
    tester.run_quick_test(30)

if __name__ == "__main__":
    main()
