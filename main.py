import time
import json
import csv
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
import os

import ping3
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import requests
import psutil
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box
from colorama import init, Fore, Style

# ローカルモジュール
from font_utils import setup_matplotlib_japanese

# カラー初期化
init(autoreset=True)
console = Console()

# matplotlibの日本語フォント設定
setup_matplotlib_japanese()

@dataclass
class PingResult:
    """Pingテストの結果を格納するクラス"""
    timestamp: str
    server: str
    latency: Optional[float]
    packet_loss: bool
    timeout: bool

@dataclass
class NetworkStats:
    """ネットワーク統計情報を格納するクラス"""
    total_packets: int
    lost_packets: int
    packet_loss_rate: float
    min_latency: float
    max_latency: float
    avg_latency: float
    jitter: float

class VALORANTServerTracker:
    """VALORANTサーバーのパケットロス追跡クラス"""
    
    # VALORANTの主要リージョンサーバー
    VALORANT_SERVERS = {
        "Tokyo (Japan)": ["52.77.252.242", "13.230.149.157"],
        "Seoul (Korea)": ["43.201.103.1", "13.124.145.30"],
        "Sydney (Australia)": ["13.236.8.0", "3.104.90.0"],
        "Singapore": ["18.143.118.0", "13.229.188.0"],
        "Mumbai (India)": ["13.234.74.0", "3.109.44.0"],
        "Hong Kong": ["18.162.190.0", "13.75.118.0"],
        "Virginia (US East)": ["52.70.118.0", "3.208.28.0"],
        "California (US West)": ["54.241.191.0", "13.57.254.0"],
        "London (EU West)": ["18.130.91.0", "3.8.37.0"],
        "Frankfurt (EU Central)": ["18.196.142.0", "3.122.224.0"]
    }
    
    # 一般的なサービスのサーバー（比較用）
    REFERENCE_SERVERS = {
        "Discord": ["162.159.130.232", "162.159.135.232"],
        "YouTube (Google)": ["8.8.8.8", "8.8.4.4"],
        "Cloudflare": ["1.1.1.1", "1.0.0.1"],
        "Amazon (AWS)": ["52.95.110.1", "54.230.0.1"],
        "Microsoft": ["13.107.42.14", "40.76.4.15"]
    }
    
    def __init__(self, timeout: float = 3.0, interval: float = 1.0):
        self.timeout = timeout
        self.interval = interval
        self.results: List[PingResult] = []
        self.reference_results: List[PingResult] = []  # 一般サービスの結果
        self.is_running = False
        self.current_region = "Tokyo (Japan)"
        self.start_time = None
        
    def get_network_interface_info(self) -> Dict:
        """ネットワークインターフェース情報を取得"""
        try:
            interfaces = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            
            active_interfaces = {}
            for interface, stats in interfaces.items():
                if stats.isup and interface in addrs:
                    for addr in addrs[interface]:
                        if addr.family.name == 'AF_INET':
                            active_interfaces[interface] = {
                                'ip': addr.address,
                                'netmask': addr.netmask,
                                'speed': stats.speed if stats.speed > 0 else 'Unknown'
                            }
            return active_interfaces
        except Exception as e:
            console.print(f"[red]ネットワーク情報取得エラー: {e}[/red]")
            return {}
    
    def ping_server(self, server_ip: str) -> PingResult:
        """指定されたサーバーにpingを送信"""
        timestamp = datetime.now().isoformat()
        
        try:
            # ping3を使用してping送信
            latency = ping3.ping(server_ip, timeout=self.timeout)
            
            if latency is None:
                return PingResult(
                    timestamp=timestamp,
                    server=server_ip,
                    latency=None,
                    packet_loss=True,
                    timeout=True
                )
            else:
                # レイテンシーをミリ秒に変換
                latency_ms = latency * 1000
                return PingResult(
                    timestamp=timestamp,
                    server=server_ip,
                    latency=latency_ms,
                    packet_loss=False,
                    timeout=False
                )
                
        except Exception as e:
            return PingResult(
                timestamp=timestamp,
                server=server_ip,
                latency=None,
                packet_loss=True,
                timeout=True
            )
    
    def run_continuous_test(self, duration_minutes: int = 10):
        """継続的なパケットロステストを実行"""
        self.is_running = True
        self.start_time = datetime.now()
        self.results.clear()
        
        end_time = self.start_time + timedelta(minutes=duration_minutes)
        servers = self.VALORANT_SERVERS[self.current_region]
        
        console.print(f"[green]パケットロステスト開始: {self.current_region}[/green]")
        console.print(f"[yellow]テスト時間: {duration_minutes}分[/yellow]")
        console.print(f"[cyan]対象サーバー: {servers}[/cyan]")
        console.print(f"[blue]終了予定時刻: {end_time.strftime('%H:%M:%S')}[/blue]")
        console.print()
        
        try:
            while self.is_running and datetime.now() < end_time:
                current_time = datetime.now()
                
                # 時間計算
                remaining_time = end_time - current_time
                remaining_total_seconds = max(0, remaining_time.total_seconds())
                remaining_minutes = int(remaining_total_seconds // 60)
                remaining_seconds = int(remaining_total_seconds % 60)
                
                # 進捗計算
                elapsed_time = current_time - self.start_time
                elapsed_total_seconds = elapsed_time.total_seconds()
                progress_percentage = min(100, (elapsed_total_seconds / (duration_minutes * 60)) * 100)
                
                # 経過時間表示用
                elapsed_minutes = int(elapsed_total_seconds // 60)
                elapsed_seconds_remainder = int(elapsed_total_seconds % 60)
                
                for server in servers:
                    if not self.is_running:
                        break
                        
                    result = self.ping_server(server)
                    self.results.append(result)
                    
                    # リアルタイム結果表示（改善された時間表示付き）
                    status = "❌ LOSS" if result.packet_loss else f"✅ {result.latency:.1f}ms"
                    progress_bar = "█" * int(progress_percentage // 5) + "░" * (20 - int(progress_percentage // 5))
                    
                    # 時間表示の改善
                    time_info = f"⏱️ {elapsed_minutes:02d}:{elapsed_seconds_remainder:02d} / {remaining_minutes:02d}:{remaining_seconds:02d}"
                    
                    console.print(
                        f"[dim]{result.timestamp[-8:]}[/dim] {server}: {status} "
                        f"[cyan]│[/cyan] [{progress_bar}] {progress_percentage:.1f}% "
                        f"[yellow]{time_info}[/yellow]"
                    )
                    
                    time.sleep(self.interval)
                
                # リアルタイム統計表示（30秒ごと）
                if int(elapsed_total_seconds) % 30 == 0 and elapsed_total_seconds > 0:
                    self._display_realtime_stats(self.results, int(elapsed_total_seconds))
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]テストが中断されました[/yellow]")
        finally:
            self.is_running = False
            console.print(f"\n[green]✅ テストが完了しました（実行時間: {elapsed_time.total_seconds():.0f}秒）[/green]")
            
    def _display_realtime_stats(self, current_results: List[PingResult], elapsed_seconds: int):
        """リアルタイム統計情報を表示"""
        if not current_results:
            return
            
        # 基本統計
        total_packets = len(current_results)
        lost_packets = len([r for r in current_results if r.packet_loss])
        successful_pings = [r for r in current_results if not r.packet_loss]
        
        if total_packets > 0:
            packet_loss_rate = (lost_packets / total_packets) * 100
            
            # 統計表示（簡潔版）
            if successful_pings:
                latencies = [r.latency for r in successful_pings]
                current_avg = statistics.mean(latencies)
                current_min = min(latencies)
                current_max = max(latencies)
                
                # 最後の5つの結果で短期トレンド計算
                recent_pings = successful_pings[-5:] if len(successful_pings) >= 5 else successful_pings
                recent_avg = statistics.mean([r.latency for r in recent_pings]) if recent_pings else 0
                
                # トレンド矢印
                trend = "📈" if recent_avg > current_avg else "📉" if recent_avg < current_avg else "➡️"
                
                stats_info = (
                    f"[dim]│ パケット: {total_packets} │ ロス: {packet_loss_rate:.1f}% │ "
                    f"レイテンシー: {current_avg:.1f}ms ({current_min:.1f}-{current_max:.1f}) {trend}[/dim]"
                )
                console.print(stats_info)
        
        # 5分おきに詳細統計を表示
        if elapsed_seconds > 0 and elapsed_seconds % 300 == 0:
            console.print(f"\n[cyan]📊 {elapsed_seconds//60}分経過時点での統計[/cyan]")
            self._display_intermediate_stats(current_results)
            console.print()
    
    def _display_intermediate_stats(self, results: List[PingResult]):
        """中間統計を表示"""
        if not results:
            return
            
        # サーバー別統計
        server_stats = {}
        for result in results:
            server = result.server
            if server not in server_stats:
                server_stats[server] = {"total": 0, "lost": 0, "latencies": []}
            
            server_stats[server]["total"] += 1
            if result.packet_loss:
                server_stats[server]["lost"] += 1
            else:
                server_stats[server]["latencies"].append(result.latency)
        
        # 表形式で表示
        table = Table(box=box.SIMPLE)
        table.add_column("サーバー", style="cyan")
        table.add_column("ロス率", style="red")
        table.add_column("平均レイテンシー", style="green")
        
        for server, stats in server_stats.items():
            loss_rate = (stats["lost"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            avg_latency = statistics.mean(stats["latencies"]) if stats["latencies"] else 0
            
            # サーバーIPを短縮表示
            server_display = server.split('.')[-1] if '.' in server else server[:15]
            
            table.add_row(
                server_display,
                f"{loss_rate:.1f}%",
                f"{avg_latency:.1f}ms" if avg_latency > 0 else "N/A"
            )
        
        console.print(table)
    
    def calculate_stats(self) -> Dict[str, NetworkStats]:
        """サーバーごとの統計情報を計算"""
        server_stats = {}
        
        # サーバーごとに結果をグループ化
        for server in set(result.server for result in self.results):
            server_results = [r for r in self.results if r.server == server]
            
            total_packets = len(server_results)
            lost_packets = sum(1 for r in server_results if r.packet_loss)
            packet_loss_rate = (lost_packets / total_packets) * 100 if total_packets > 0 else 0
            
            # レイテンシー統計（成功したパケットのみ）
            successful_pings = [r.latency for r in server_results if r.latency is not None]
            
            if successful_pings:
                min_latency = min(successful_pings)
                max_latency = max(successful_pings)
                avg_latency = statistics.mean(successful_pings)
                
                # ジッターの計算（標準偏差）
                jitter = statistics.stdev(successful_pings) if len(successful_pings) > 1 else 0
            else:
                min_latency = max_latency = avg_latency = jitter = 0
            
            server_stats[server] = NetworkStats(
                total_packets=total_packets,
                lost_packets=lost_packets,
                packet_loss_rate=packet_loss_rate,
                min_latency=min_latency,
                max_latency=max_latency,
                avg_latency=avg_latency,
                jitter=jitter
            )
            
        return server_stats
    
    def display_results(self):
        """結果をリッチなテーブル形式で表示"""
        if not self.results:
            console.print("[red]表示する結果がありません[/red]")
            return
            
        stats = self.calculate_stats()
        
        # サマリーテーブル
        table = Table(title=f"VALORANTパケットロス解析結果 - {self.current_region}", box=box.ROUNDED)
        table.add_column("サーバー", style="cyan")
        table.add_column("総パケット", justify="right", style="green")
        table.add_column("ロスト", justify="right", style="red")
        table.add_column("ロス率", justify="right", style="magenta")
        table.add_column("平均レイテンシー", justify="right", style="yellow")
        table.add_column("最小/最大", justify="right", style="blue")
        table.add_column("ジッター", justify="right", style="white")
        
        for server, stat in stats.items():
            loss_color = "red" if stat.packet_loss_rate > 5 else "yellow" if stat.packet_loss_rate > 1 else "green"
            latency_color = "red" if stat.avg_latency > 100 else "yellow" if stat.avg_latency > 50 else "green"
            
            table.add_row(
                server,
                str(stat.total_packets),
                str(stat.lost_packets),
                f"[{loss_color}]{stat.packet_loss_rate:.1f}%[/{loss_color}]",
                f"[{latency_color}]{stat.avg_latency:.1f}ms[/{latency_color}]",
                f"{stat.min_latency:.1f}/{stat.max_latency:.1f}ms",
                f"{stat.jitter:.1f}ms"
            )
        
        console.print()
        console.print(table)
        
        # 問題分析
        self.analyze_issues(stats)
    
    def analyze_issues(self, stats: Dict[str, NetworkStats]):
        """ネットワーク問題の分析と推奨事項"""
        if not stats:
            console.print("[yellow]⚠️ 分析するデータがありません[/yellow]")
            return
            
        issues = []
        recommendations = []
        
        overall_loss_rate = sum(s.packet_loss_rate for s in stats.values()) / len(stats) if stats else 0
        
        # レイテンシーデータがある場合のみ計算
        latency_values = [s.avg_latency for s in stats.values() if s.avg_latency > 0]
        overall_avg_latency = sum(latency_values) / len(latency_values) if latency_values else 0
        
        # パケットロス分析
        if overall_loss_rate > 5:
            issues.append("❌ 高いパケットロス率が検出されました")
            recommendations.extend([
                "ネットワーク接続の確認",
                "ルーターの再起動",
                "有線接続への変更を検討",
                "ISPへの問い合わせ"
            ])
        elif overall_loss_rate > 1:
            issues.append("⚠️ 軽微なパケットロスが検出されました")
            recommendations.extend([
                "WiFi信号強度の確認",
                "他のネットワーク使用量の確認"
            ])
        
        # レイテンシー分析
        if overall_avg_latency > 100:
            issues.append("❌ 高いレイテンシーが検出されました")
            recommendations.extend([
                "地理的に近いサーバーの選択",
                "VPNの無効化",
                "ネットワーク最適化ツールの使用"
            ])
        elif overall_avg_latency > 50:
            issues.append("⚠️ やや高いレイテンシーです")
            recommendations.append("ゲーム設定でのサーバー選択の見直し")
        
        # ジッター分析
        high_jitter_servers = [s for s in stats.values() if s.jitter > 10]
        if high_jitter_servers:
            issues.append("❌ 不安定な接続（高ジッター）が検出されました")
            recommendations.extend([
                "ネットワーク帯域の使用量確認",
                "QoS設定の調整",
                "ゲーム専用ネットワークの検討"
            ])
        
        # 結果表示
        if issues:
            console.print("\n[bold red]検出された問題:[/bold red]")
            for issue in issues:
                console.print(f"  {issue}")
            
            console.print("\n[bold green]推奨事項:[/bold green]")
            for i, rec in enumerate(recommendations, 1):
                console.print(f"  {i}. {rec}")
        else:
            console.print("\n[bold green]✅ ネットワーク状態は良好です！[/bold green]")
    
    def save_results(self, filename: str = None):
        """結果をファイルに保存"""
        if not self.results:
            console.print("[red]保存する結果がありません[/red]")
            return
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"valorant_packet_loss_{timestamp}"
        
        # CSV形式で保存
        csv_file = f"{filename}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Server', 'Latency(ms)', 'Packet_Loss', 'Timeout'])
            
            for result in self.results:
                writer.writerow([
                    result.timestamp,
                    result.server,
                    result.latency if result.latency else 'N/A',
                    result.packet_loss,
                    result.timeout
                ])
        
        # JSON形式で統計データを保存
        stats = self.calculate_stats()
        json_file = f"{filename}_stats.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            stats_dict = {server: asdict(stat) for server, stat in stats.items()}
            json.dump({
                'test_info': {
                    'region': self.current_region,
                    'start_time': self.start_time.isoformat() if self.start_time else None,
                    'duration_minutes': (datetime.now() - self.start_time).total_seconds() / 60 if self.start_time else 0
                },
                'server_stats': stats_dict
            }, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]結果が保存されました:[/green]")
        console.print(f"  📊 詳細データ: {csv_file}")
        console.print(f"  📈 統計情報: {json_file}")
    
    def create_visualization(self, filename: str = None):
        """結果の可視化グラフを作成"""
        if not self.results:
            console.print("[red]可視化する結果がありません[/red]")
            return
            
        # データフレーム作成
        df = pd.DataFrame([asdict(result) for result in self.results])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['latency'] = pd.to_numeric(df['latency'], errors='coerce')
        
        # グラフ作成
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'VALORANT パケットロス解析 - {self.current_region}', 
                    fontsize=16, fontweight='bold')
        
        # 1. レイテンシーの時系列グラフ
        for server in df['server'].unique():
            server_data = df[df['server'] == server]
            ax1.plot(server_data['timestamp'], server_data['latency'], 
                    label=server.split('.')[-1], alpha=0.7, linewidth=1.5)
        ax1.set_title('レイテンシーの推移')
        ax1.set_ylabel('レイテンシー (ms)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. パケットロス率
        stats = self.calculate_stats()
        servers = list(stats.keys())
        loss_rates = [stats[server].packet_loss_rate for server in servers]
        
        colors = ['red' if rate > 5 else 'orange' if rate > 1 else 'green' for rate in loss_rates]
        bars = ax2.bar(range(len(servers)), loss_rates, color=colors, alpha=0.7)
        ax2.set_title('サーバー別パケットロス率')
        ax2.set_ylabel('パケットロス率 (%)')
        ax2.set_xticks(range(len(servers)))
        ax2.set_xticklabels([s.split('.')[-1] for s in servers], rotation=45)
        
        # バーの上に数値を表示
        for bar, rate in zip(bars, loss_rates):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f'{rate:.1f}%', ha='center', va='bottom')
        
        # 3. レイテンシー分布
        successful_latencies = df[df['latency'].notna()]['latency']
        if len(successful_latencies) > 0:
            ax3.hist(successful_latencies, bins=30, color='skyblue', 
                    alpha=0.7, edgecolor='black')
            ax3.set_title('レイテンシー分布')
            ax3.set_xlabel('レイテンシー (ms)')
            ax3.set_ylabel('頻度')
            ax3.axvline(successful_latencies.mean(), color='red', linestyle='--', 
                        label=f'平均: {successful_latencies.mean():.1f}ms')
            ax3.legend()
        else:
            ax3.text(0.5, 0.5, 'データなし', ha='center', va='center', 
                    transform=ax3.transAxes, fontsize=14)
            ax3.set_title('レイテンシー分布')
        
        # 4. サーバー別統計比較
        avg_latencies = [stats[server].avg_latency for server in servers]
        jitters = [stats[server].jitter for server in servers]
        
        x = range(len(servers))
        width = 0.35
        bars1 = ax4.bar([i - width/2 for i in x], avg_latencies, width, 
                        label='平均レイテンシー', alpha=0.7, color='blue')
        bars2 = ax4.bar([i + width/2 for i in x], jitters, width, 
                        label='ジッター', alpha=0.7, color='orange')
        ax4.set_title('サーバー別パフォーマンス比較')
        ax4.set_ylabel('時間 (ms)')
        ax4.set_xticks(x)
        ax4.set_xticklabels([s.split('.')[-1] for s in servers], rotation=45)
        ax4.legend()
        
        # バーの上に数値を表示
        for bar, value in zip(bars1, avg_latencies):
            if value > 0:
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{value:.1f}', ha='center', va='bottom', fontsize=8)
        
        for bar, value in zip(bars2, jitters):
            if value > 0:
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{value:.1f}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"valorant_analysis_{timestamp}.png"
        else:
            filename = f"{filename}.png"
            
        plt.savefig(filename, dpi=300, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        console.print(f"[green]グラフが保存されました: {filename}[/green]")
        plt.show()
    
    def test_reference_servers(self, duration_minutes: int = 5):
        """一般サービスサーバーのテストを実行"""
        console.print(f"[cyan]📡 一般サービスへの接続テストを開始（{duration_minutes}分間）[/cyan]")
        
        self.reference_results.clear()
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # 各サービスから1つずつサーバーを選択
        test_servers = {}
        for service, servers in self.REFERENCE_SERVERS.items():
            test_servers[service] = servers[0]  # 最初のサーバーを使用
        
        console.print("[yellow]テスト対象サービス:[/yellow]")
        for service, server in test_servers.items():
            console.print(f"  • {service}: {server}")
        console.print(f"[blue]終了予定時刻: {end_time.strftime('%H:%M:%S')}[/blue]")
        console.print()
        
        try:
            while datetime.now() < end_time:
                current_time = datetime.now()
                
                # 時間計算
                remaining_time = end_time - current_time
                remaining_total_seconds = max(0, remaining_time.total_seconds())
                remaining_minutes = int(remaining_total_seconds // 60)
                remaining_seconds = int(remaining_total_seconds % 60)
                
                # 進捗計算
                elapsed_time = current_time - start_time
                elapsed_total_seconds = elapsed_time.total_seconds()
                progress_percentage = min(100, (elapsed_total_seconds / (duration_minutes * 60)) * 100)
                
                # 経過時間表示用
                elapsed_minutes = int(elapsed_total_seconds // 60)
                elapsed_seconds_remainder = int(elapsed_total_seconds % 60)
                
                for service, server in test_servers.items():
                    result = self.ping_server(server)
                    # サービス名を記録するため、serverフィールドを拡張
                    result.server = f"{service}|{server}"
                    self.reference_results.append(result)
                    
                    # リアルタイム結果表示（改善された時間表示付き）
                    status = "❌ LOSS" if result.packet_loss else f"✅ {result.latency:.1f}ms"
                    progress_bar = "█" * int(progress_percentage // 5) + "░" * (20 - int(progress_percentage // 5))
                    
                    # 時間表示の改善
                    time_info = f"⏱️ {elapsed_minutes:02d}:{elapsed_seconds_remainder:02d} / {remaining_minutes:02d}:{remaining_seconds:02d}"
                    
                    console.print(
                        f"[dim]{result.timestamp[-8:]}[/dim] {service}: {status} "
                        f"[cyan]│[/cyan] [{progress_bar}] {progress_percentage:.1f}% "
                        f"[yellow]{time_info}[/yellow]"
                    )
                    
                    time.sleep(self.interval / len(test_servers))  # 間隔を調整
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]一般サービステストが中断されました[/yellow]")
        
        elapsed_time = datetime.now() - start_time
        console.print(f"\n[green]✅ 一般サービステストが完了しました（実行時間: {elapsed_time.total_seconds():.0f}秒）[/green]")
        
    def compare_with_reference_servers(self) -> Dict:
        """VALORANTサーバーと一般サービスの結果を比較"""
        if not self.reference_results:
            return {"error": "一般サービスのテスト結果がありません"}
        
        if not self.results:
            return {"error": "VALORANTサーバーのテスト結果がありません"}
        
        # VALORANT統計を計算
        valorant_stats = self.calculate_stats()
        if not valorant_stats:
            return {"error": "VALORANTサーバーの統計データを計算できませんでした"}
        
        valorant_avg_loss = statistics.mean([stat.packet_loss_rate for stat in valorant_stats.values()])
        
        # レイテンシーのデータがあるかチェック
        valorant_latency_data = [stat.avg_latency for stat in valorant_stats.values() if stat.avg_latency > 0]
        valorant_avg_latency = statistics.mean(valorant_latency_data) if valorant_latency_data else 0
        
        # 一般サービス統計を計算
        reference_stats = {}
        for service in self.REFERENCE_SERVERS.keys():
            service_results = [r for r in self.reference_results if r.server.startswith(f"{service}|")]
            if service_results:
                total_packets = len(service_results)
                lost_packets = sum(1 for r in service_results if r.packet_loss)
                packet_loss_rate = (lost_packets / total_packets) * 100 if total_packets > 0 else 0
                
                successful_pings = [r.latency for r in service_results if r.latency is not None]
                avg_latency = statistics.mean(successful_pings) if successful_pings else 0
                
                reference_stats[service] = {
                    'packet_loss_rate': packet_loss_rate,
                    'avg_latency': avg_latency,
                    'total_packets': total_packets
                }
        
        if not reference_stats:
            return {"error": "一般サービスの統計データを計算できませんでした"}
        
        # 比較結果を生成
        reference_avg_loss = statistics.mean([stat['packet_loss_rate'] for stat in reference_stats.values()])
        
        # 一般サービスのレイテンシーデータがあるかチェック
        reference_latency_data = [stat['avg_latency'] for stat in reference_stats.values() if stat['avg_latency'] > 0]
        reference_avg_latency = statistics.mean(reference_latency_data) if reference_latency_data else 0
        
        comparison = {
            'valorant': {
                'avg_packet_loss': valorant_avg_loss,
                'avg_latency': valorant_avg_latency
            },
            'reference': {
                'avg_packet_loss': reference_avg_loss,
                'avg_latency': reference_avg_latency,
                'services': reference_stats
            },
            'analysis': self._analyze_comparison(valorant_avg_loss, reference_avg_loss, valorant_avg_latency, reference_avg_latency)
        }
        
        return comparison
    
    def _analyze_comparison(self, val_loss: float, ref_loss: float, val_latency: float, ref_latency: float) -> Dict:
        """比較結果の分析"""
        analysis = {
            'problem_source': 'unknown',
            'confidence': 'low',
            'recommendation': [],
            'details': {}
        }
        
        # パケットロス比較
        loss_diff = val_loss - ref_loss
        latency_diff = val_latency - ref_latency
        
        if loss_diff > 3:  # VALORANTの方が3%以上高い
            if ref_loss < 1:  # 一般サービスは正常
                analysis['problem_source'] = 'valorant_servers'
                analysis['confidence'] = 'high'
                analysis['recommendation'].extend([
                    "VALORANTサーバーに問題がある可能性が高いです",
                    "別のVALORANTリージョンを試してください",
                    "Riot Gamesの公式ステータスページを確認してください"
                ])
            else:
                analysis['problem_source'] = 'network_general'
                analysis['confidence'] = 'medium'
                analysis['recommendation'].extend([
                    "全般的なネットワーク問題の可能性があります",
                    "ISPに問い合わせることを検討してください"
                ])
        elif loss_diff < -1:  # 一般サービスの方が悪い
            analysis['problem_source'] = 'network_routing'
            analysis['confidence'] = 'medium'
            analysis['recommendation'].extend([
                "特定の経路に問題がある可能性があります",
                "VPNの使用を検討してください"
            ])
        else:  # 似たような結果
            if val_loss > 2:
                analysis['problem_source'] = 'network_general'
                analysis['confidence'] = 'high'
                analysis['recommendation'].extend([
                    "全般的なネットワーク品質の問題です",
                    "Wi-Fi接続の場合は有線接続を試してください",
                    "他のデバイスのネットワーク使用量を確認してください"
                ])
            else:
                analysis['problem_source'] = 'no_significant_issue'
                analysis['confidence'] = 'high'
                analysis['recommendation'].append("ネットワーク品質は正常範囲内です")
        
        # レイテンシー比較
        if latency_diff > 20:  # VALORANTの方が20ms以上高い
            analysis['recommendation'].append("VALORANTサーバーへの経路に遅延があります")
            if analysis['problem_source'] == 'no_significant_issue':
                analysis['problem_source'] = 'valorant_latency'
        
        analysis['details'] = {
            'packet_loss_diff': loss_diff,
            'latency_diff': latency_diff,
            'valorant_loss': val_loss,
            'reference_loss': ref_loss,
            'valorant_latency': val_latency,
            'reference_latency': ref_latency
        }
        
        return analysis

    def display_comparison_results(self):
        """VALORANTと一般サービスの比較結果を表示"""
        comparison = self.compare_with_reference_servers()
        
        if "error" in comparison:
            console.print(f"[red]❌ {comparison['error']}[/red]")
            console.print("[yellow]💡 比較分析を行うには、両方のテストを実行してください:[/yellow]")
            console.print("  1. メニュー「3」で一般サービステストを実行")
            console.print("  2. メニュー「2」でVALORANTサーバーテストを実行")
            console.print("  3. または、メニュー「4」で包括的テストを実行")
            return
        
        console.print()
        console.print(Panel.fit("🔍 問題の原因分析", style="bold blue"))
        
        # 比較テーブル
        table = Table(title="VALORANTサーバー vs 一般サービス比較", box=box.ROUNDED)
        table.add_column("項目", style="cyan")
        table.add_column("VALORANTサーバー", justify="right", style="red")
        table.add_column("一般サービス", justify="right", style="green")
        table.add_column("差分", justify="right", style="yellow")
        
        val_data = comparison['valorant']
        ref_data = comparison['reference']
        
        # パケットロス率
        loss_diff = val_data['avg_packet_loss'] - ref_data['avg_packet_loss']
        loss_color = "red" if loss_diff > 2 else "yellow" if loss_diff > 0.5 else "green"
        table.add_row(
            "パケットロス率",
            f"{val_data['avg_packet_loss']:.1f}%",
            f"{ref_data['avg_packet_loss']:.1f}%",
            f"[{loss_color}]{loss_diff:+.1f}%[/{loss_color}]"
        )
        
        # 平均レイテンシー
        latency_diff = val_data['avg_latency'] - ref_data['avg_latency']
        latency_color = "red" if latency_diff > 20 else "yellow" if latency_diff > 10 else "green"
        table.add_row(
            "平均レイテンシー",
            f"{val_data['avg_latency']:.1f}ms",
            f"{ref_data['avg_latency']:.1f}ms",
            f"[{latency_color}]{latency_diff:+.1f}ms[/{latency_color}]"
        )
        
        console.print(table)
        
        # 個別サービス結果
        console.print()
        service_table = Table(title="一般サービス個別結果", box=box.SIMPLE)
        service_table.add_column("サービス", style="cyan")
        service_table.add_column("パケットロス率", justify="right")
        service_table.add_column("平均レイテンシー", justify="right")
        service_table.add_column("状態", justify="center")
        
        for service, stats in ref_data['services'].items():
            loss_rate = stats['packet_loss_rate']
            avg_latency = stats['avg_latency']
            
            # 状態判定
            if loss_rate > 2:
                status = "[red]❌ 問題あり[/red]"
            elif loss_rate > 0.5:
                status = "[yellow]⚠️ 注意[/yellow]"
            else:
                status = "[green]✅ 正常[/green]"
            
            service_table.add_row(
                service,
                f"{loss_rate:.1f}%",
                f"{avg_latency:.1f}ms" if avg_latency > 0 else "N/A",
                status
            )
        
        console.print(service_table)
        
        # 分析結果
        analysis = comparison['analysis']
        console.print()
        console.print(Panel.fit("📋 分析結果と推奨事項", style="bold yellow"))
        
        # 問題の原因
        source_text = {
            'valorant_servers': "🎯 VALORANTサーバー側の問題",
            'network_general': "🌐 全般的なネットワーク問題", 
            'network_routing': "🛣️ ネットワーク経路の問題",
            'valorant_latency': "⏱️ VALORANTサーバーへのレイテンシー問題",
            'no_significant_issue': "✅ 重大な問題は検出されませんでした"
        }.get(analysis['problem_source'], "❓ 不明")
        
        confidence_color = {
            'high': 'green',
            'medium': 'yellow', 
            'low': 'red'
        }.get(analysis['confidence'], 'white')
        
        console.print(f"問題の原因: {source_text}")
        console.print(f"信頼度: [{confidence_color}]{analysis['confidence'].upper()}[/{confidence_color}]")
        console.print()
        
        # 推奨事項
        console.print("[bold]推奨事項:[/bold]")
        for i, recommendation in enumerate(analysis['recommendation'], 1):
            console.print(f"  {i}. {recommendation}")
    
    def run_comprehensive_test(self, duration_minutes: int = 10):
        """VALORANTサーバーと一般サービスの包括的テスト"""
        console.print("[bold green]🚀 包括的ネットワーク品質テストを開始[/bold green]")
        console.print(f"[yellow]総テスト時間: {duration_minutes}分[/yellow]")
        
        half_duration = duration_minutes // 2
        
        console.print()
        
        # Step 1: 一般サービステスト
        console.print("[bold cyan]Step 1/2: 一般サービス接続テスト[/bold cyan]")
        console.print(f"[dim]この段階の時間: {half_duration}分[/dim]")
        self.test_reference_servers(half_duration)
        
        console.print()
        console.print("[bold cyan]Step 2/2: VALORANTサーバーテスト[/bold cyan]")
        console.print(f"[dim]この段階の時間: {half_duration}分[/dim]")
        # Step 2: VALORANTサーバーテスト
        self.run_continuous_test(half_duration)
        
        console.print()
        console.print("[bold cyan]Step 3: 結果分析[/bold cyan]")
        console.print("[dim]分析を実行しています...[/dim]")
        # Step 3: 結果表示と比較
        self.display_results()
        self.display_comparison_results()
        
        console.print("\n[bold green]🎉 包括的テストが完了しました！[/bold green]")
    
    def import_results(self, filename: str = None):
        """保存された結果をインポート"""
        if filename is None:
            filename = console.input("[green]インポートするファイル名 (.csvまたは_stats.json): [/green]").strip()
            if not filename:
                console.print("[red]❌ ファイル名が指定されていません[/red]")
                return False
        
        try:
            # CSVファイルのインポート
            if filename.endswith('.csv'):
                return self._import_csv_results(filename)
            # JSONファイルのインポート (統計データのみ)
            elif filename.endswith('_stats.json') or filename.endswith('.json'):
                return self._import_json_stats(filename)
            else:
                console.print("[red]❌ サポートされていないファイル形式です (.csvまたは_stats.json)[/red]")
                return False
                
        except FileNotFoundError:
            console.print(f"[red]❌ ファイルが見つかりません: {filename}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ インポートエラー: {e}[/red]")
            return False
    
    def _import_csv_results(self, filename: str) -> bool:
        """CSVファイルから結果をインポート"""
        console.print(f"[cyan]📊 CSVファイルをインポート中: {filename}[/cyan]")
        
        imported_results = []
        
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # CSVデータからPingResultオブジェクトを再構築
                latency = None if row['Latency(ms)'] == 'N/A' else float(row['Latency(ms)'])
                packet_loss = row['Packet_Loss'].lower() == 'true'
                timeout = row['Timeout'].lower() == 'true'
                
                result = PingResult(
                    timestamp=row['Timestamp'],
                    server=row['Server'],
                    latency=latency,
                    packet_loss=packet_loss,
                    timeout=timeout
                )
                imported_results.append(result)
        
        # インポートしたデータで現在の結果を置き換えるか確認
        if self.results:
            choice = console.input("[yellow]現在のデータを置き換えますか？ (y/N): [/yellow]").strip().lower()
            if choice != 'y':
                # 既存データに追加
                self.results.extend(imported_results)
                console.print(f"[green]✅ {len(imported_results)}件のデータを追加しました[/green]")
            else:
                # データを置き換え
                self.results = imported_results
                console.print(f"[green]✅ {len(imported_results)}件のデータをインポートしました（置き換え）[/green]")
        else:
            self.results = imported_results
            console.print(f"[green]✅ {len(imported_results)}件のデータをインポートしました[/green]")
        
        # リージョン推定（サーバーIPから）
        self._estimate_region_from_servers()
        return True
    
    def _import_json_stats(self, filename: str) -> bool:
        """JSONファイルから統計データをインポート"""
        console.print(f"[cyan]📈 JSON統計ファイルをインポート中: {filename}[/cyan]")
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # テスト情報を復元
        if 'test_info' in data:
            test_info = data['test_info']
            if 'region' in test_info:
                self.current_region = test_info['region']
                console.print(f"[green]リージョン設定: {self.current_region}[/green]")
            
            if 'start_time' in test_info and test_info['start_time']:
                self.start_time = datetime.fromisoformat(test_info['start_time'])
                console.print(f"[green]テスト開始時間: {self.start_time}[/green]")
        
        # 統計データを表示
        if 'server_stats' in data:
            console.print("[cyan]インポートされた統計データ:[/cyan]")
            
            # 統計テーブル作成
            table = Table(title=f"インポートされた統計 - {self.current_region}", box=box.ROUNDED)
            table.add_column("サーバー", style="cyan")
            table.add_column("総パケット", justify="right", style="green")
            table.add_column("ロスト", justify="right", style="red")
            table.add_column("ロス率", justify="right", style="magenta")
            table.add_column("平均レイテンシー", justify="right", style="yellow")
            table.add_column("ジッター", justify="right", style="white")
            
            for server, stats in data['server_stats'].items():
                loss_color = "red" if stats['packet_loss_rate'] > 5 else "yellow" if stats['packet_loss_rate'] > 1 else "green"
                latency_color = "red" if stats['avg_latency'] > 100 else "yellow" if stats['avg_latency'] > 50 else "green"
                
                table.add_row(
                    server,
                    str(stats['total_packets']),
                    str(stats['lost_packets']),
                    f"[{loss_color}]{stats['packet_loss_rate']:.1f}%[/{loss_color}]",
                    f"[{latency_color}]{stats['avg_latency']:.1f}ms[/{latency_color}]",
                    f"{stats['jitter']:.1f}ms"
                )
            
            console.print(table)
            console.print(f"[green]✅ 統計データをインポートしました[/green]")
            console.print("[yellow]💡 詳細データが必要な場合は、対応するCSVファイルもインポートしてください[/yellow]")
        
        return True
    
    def _estimate_region_from_servers(self):
        """サーバーIPから推定リージョンを設定"""
        if not self.results:
            return
        
        # 結果から使用されているサーバーを取得
        used_servers = set(result.server for result in self.results)
        
        # 各リージョンのサーバーと比較
        for region, servers in self.VALORANT_SERVERS.items():
            if any(server in used_servers for server in servers):
                self.current_region = region
                console.print(f"[green]リージョンを推定しました: {region}[/green]")
                break
    
    def list_saved_files(self):
        """保存されたファイルの一覧を表示"""
        console.print("[cyan]📁 保存されたファイル一覧:[/cyan]")
        
        # 現在のディレクトリのファイルを検索
        csv_files = []
        json_files = []
        
        try:
            for file in os.listdir('.'):
                if file.endswith('.csv') and ('valorant' in file.lower() or 'demo' in file.lower()):
                    csv_files.append(file)
                elif file.endswith('_stats.json') or (file.endswith('.json') and ('valorant' in file.lower() or 'demo' in file.lower())):
                    json_files.append(file)
            
            if csv_files or json_files:
                table = Table(title="利用可能なファイル", box=box.SIMPLE)
                table.add_column("ファイル名", style="cyan")
                table.add_column("タイプ", style="yellow")
                table.add_column("更新日時", style="green")
                
                # CSVファイル
                for file in sorted(csv_files):
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(file))
                        table.add_row(file, "CSV (詳細データ)", mtime.strftime("%Y-%m-%d %H:%M"))
                    except:
                        table.add_row(file, "CSV (詳細データ)", "不明")
                
                # JSONファイル
                for file in sorted(json_files):
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(file))
                        table.add_row(file, "JSON (統計データ)", mtime.strftime("%Y-%m-%d %H:%M"))
                    except:
                        table.add_row(file, "JSON (統計データ)", "不明")
                
                console.print(table)
            else:
                console.print("[yellow]保存されたファイルが見つかりません[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ ファイル一覧の取得エラー: {e}[/red]")
    
    def quick_import_menu(self):
        """クイックインポートメニュー"""
        console.print("\n[bold cyan]📥 データインポート[/bold cyan]")
        
        # ファイル一覧を表示
        self.list_saved_files()
        
        console.print("\n[yellow]インポートオプション:[/yellow]")
        console.print("1. ファイル名を直接入力")
        console.print("2. 最新のファイルを自動選択")
        console.print("3. キャンセル")
        
        choice = console.input("\n[green]選択してください (1-3): [/green]").strip()
        
        if choice == "1":
            filename = console.input("[green]ファイル名を入力: [/green]").strip()
            if filename:
                self.import_results(filename)
        
        elif choice == "2":
            # 最新のファイルを自動選択
            try:
                files = []
                for file in os.listdir('.'):
                    if (file.endswith('.csv') or file.endswith('_stats.json')) and \
                       ('valorant' in file.lower() or 'demo' in file.lower()):
                        mtime = os.path.getmtime(file)
                        files.append((file, mtime))
                
                if files:
                    # 最新のファイルを選択
                    latest_file = max(files, key=lambda x: x[1])[0]
                    console.print(f"[cyan]最新ファイルを選択: {latest_file}[/cyan]")
                    self.import_results(latest_file)
                else:
                    console.print("[yellow]インポート可能なファイルが見つかりません[/yellow]")
                    
            except Exception as e:
                console.print(f"[red]❌ ファイル選択エラー: {e}[/red]")
        
        elif choice == "3":
            console.print("[yellow]インポートをキャンセルしました[/yellow]")
        
        else:
            console.print("[red]❌ 無効な選択です[/red]")

def main():
    """メイン関数"""
    console.print(Panel.fit(
        "[bold blue]VALORANT パケットロス追跡・解析ツール[/bold blue]\n"
        "[yellow]ネットワーク品質を監視してゲーム体験を最適化[/yellow]",
        box=box.DOUBLE
    ))
    
    tracker = VALORANTServerTracker()
    
    while True:
        console.print("\n[bold cyan]メニュー:[/bold cyan]")
        console.print("1. リージョン選択")
        console.print("2. VALORANTサーバーテスト")
        console.print("3. 一般サービステスト")
        console.print("4. 包括的テスト（推奨）🎯")
        console.print("5. 結果表示")
        console.print("6. 比較分析🔍")
        console.print("7. 結果保存")
        console.print("8. データインポート📥")
        console.print("9. グラフ作成")
        console.print("10. ネットワーク情報表示")
        console.print("0. 終了")
        
        choice = console.input("\n[green]選択してください (0-10): [/green]")
        
        if choice == "1":
            # リージョン選択
            console.print("\n[bold yellow]利用可能なリージョン:[/bold yellow]")
            regions = list(tracker.VALORANT_SERVERS.keys())
            for i, region in enumerate(regions, 1):
                marker = "👉" if region == tracker.current_region else "  "
                console.print(f"{marker} {i}. {region}")
            
            try:
                region_choice = int(console.input("\n[green]リージョンを選択 (1-{}): [/green]".format(len(regions))))
                if 1 <= region_choice <= len(regions):
                    tracker.current_region = regions[region_choice - 1]
                    console.print(f"[green]✅ リージョンを {tracker.current_region} に設定しました[/green]")
                else:
                    console.print("[red]❌ 無効な選択です[/red]")
            except ValueError:
                console.print("[red]❌ 数値を入力してください[/red]")
                
        elif choice == "2":
            # VALORANTサーバーテスト
            try:
                duration = int(console.input("[green]テスト時間を分で入力 (デフォルト: 5): [/green]") or "5")
                tracker.run_continuous_test(duration)
            except ValueError:
                console.print("[red]❌ 有効な数値を入力してください[/red]")
            except KeyboardInterrupt:
                console.print("\n[yellow]テストが中断されました[/yellow]")
                
        elif choice == "3":
            # 一般サービステスト
            try:
                duration = int(console.input("[green]テスト時間を分で入力 (デフォルト: 3): [/green]") or "3")
                tracker.test_reference_servers(duration)
            except ValueError:
                console.print("[red]❌ 有効な数値を入力してください[/red]")
            except KeyboardInterrupt:
                console.print("\n[yellow]テストが中断されました[/yellow]")
                
        elif choice == "4":
            # 包括的テスト
            try:
                duration = int(console.input("[green]総テスト時間を分で入力 (デフォルト: 10): [/green]") or "10")
                tracker.run_comprehensive_test(duration)
            except ValueError:
                console.print("[red]❌ 有効な数値を入力してください[/red]")
            except KeyboardInterrupt:
                console.print("\n[yellow]テストが中断されました[/yellow]")
                
        elif choice == "5":
            # 結果表示
            tracker.display_results()
            
        elif choice == "6":
            # 比較分析
            tracker.display_comparison_results()
            
        elif choice == "7":
            # 結果保存
            filename = console.input("[green]ファイル名 (空白でデフォルト): [/green]").strip()
            tracker.save_results(filename if filename else None)
            
        elif choice == "8":
            # データインポート
            tracker.quick_import_menu()
            
        elif choice == "9":
            # グラフ作成
            filename = console.input("[green]グラフファイル名 (空白でデフォルト): [/green]").strip()
            tracker.create_visualization(filename if filename else None)
            
        elif choice == "10":
            # ネットワーク情報表示
            interfaces = tracker.get_network_interface_info()
            if interfaces:
                table = Table(title="ネットワークインターフェース情報")
                table.add_column("インターフェース", style="cyan")
                table.add_column("IPアドレス", style="green")
                table.add_column("ネットマスク", style="yellow")
                table.add_column("速度", style="magenta")
                
                for interface, info in interfaces.items():
                    table.add_row(
                        interface,
                        info['ip'],
                        info['netmask'],
                        f"{info['speed']} Mbps" if isinstance(info['speed'], (int, float)) else str(info['speed'])
                    )
                console.print(table)
            else:
                console.print("[red]ネットワーク情報を取得できませんでした[/red]")
                
        elif choice == "0":
            # 終了
            console.print("[yellow]👋 プログラムを終了します[/yellow]")
            break
            
        else:
            console.print("[red]❌ 無効な選択です。0-10の数字を入力してください[/red]")

if __name__ == "__main__":
    main()