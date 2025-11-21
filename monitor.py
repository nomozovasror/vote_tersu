#!/usr/bin/env python3
"""
Real-time System Monitor
Displays live WebSocket connection and system statistics
"""

import asyncio
import aiohttp
import json
import sys
import argparse
from datetime import datetime
from typing import Optional

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'
    CLEAR_LINE = '\033[K'
    MOVE_UP = '\033[F'


def clear_screen():
    """Clear terminal screen"""
    print('\033[2J\033[H', end='')


def format_size(bytes_value: float) -> str:
    """Format bytes to human readable size"""
    if bytes_value >= 1024:
        return f"{bytes_value / 1024:.1f} GB"
    return f"{bytes_value:.1f} MB"


def get_status_color(value: float, warning: float, critical: float) -> str:
    """Get color based on threshold"""
    if value >= critical:
        return Colors.RED
    elif value >= warning:
        return Colors.YELLOW
    return Colors.GREEN


async def fetch_stats(api_url: str) -> Optional[dict]:
    """Fetch stats from API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/ws-stats", timeout=5) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}"}
    except aiohttp.ClientConnectorError:
        return {"error": "Connection refused"}
    except asyncio.TimeoutError:
        return {"error": "Timeout"}
    except Exception as e:
        return {"error": str(e)}


def display_stats(stats: dict, previous_stats: Optional[dict] = None):
    """Display statistics in a nice format"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Header
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}📊 Real-time System Monitor{Colors.END}  |  {timestamp}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

    if "error" in stats:
        print(f"{Colors.RED}❌ Error: {stats['error']}{Colors.END}")
        print(f"\n{Colors.YELLOW}Checking connection...{Colors.END}")
        return

    # WebSocket Connections
    vote_conns = stats.get('total_vote_connections', 0)
    display_conns = stats.get('total_display_connections', 0)
    total_conns = vote_conns + display_conns

    prev_total = 0
    if previous_stats:
        prev_vote = previous_stats.get('total_vote_connections', 0)
        prev_display = previous_stats.get('total_display_connections', 0)
        prev_total = prev_vote + prev_display

    conn_diff = total_conns - prev_total
    conn_indicator = ""
    if conn_diff > 0:
        conn_indicator = f"{Colors.GREEN}↑ +{conn_diff}{Colors.END}"
    elif conn_diff < 0:
        conn_indicator = f"{Colors.RED}↓ {conn_diff}{Colors.END}"
    else:
        conn_indicator = f"{Colors.BLUE}→{Colors.END}"

    print(f"{Colors.BOLD}🔌 WebSocket Connections:{Colors.END}")
    print(f"  Total:      {Colors.BOLD}{total_conns:4d}{Colors.END}  {conn_indicator}")
    print(f"  Voting:     {Colors.CYAN}{vote_conns:4d}{Colors.END}")
    print(f"  Display:    {Colors.MAGENTA}{display_conns:4d}{Colors.END}")
    print(f"  Events:     {stats.get('events_with_vote_connections', 0)} active")

    # System Resources
    system = stats.get('system', {})
    if system:
        cpu = system.get('cpu_percent', 0)
        memory_mb = system.get('memory_mb', 0)
        open_files = system.get('open_files', 0)
        threads = system.get('threads', 0)
        connections = system.get('connections', 0)

        print(f"\n{Colors.BOLD}💻 System Resources:{Colors.END}")

        # CPU
        cpu_color = get_status_color(cpu, 70, 90)
        cpu_bar = '█' * int(cpu / 2) + '░' * (50 - int(cpu / 2))
        print(f"  CPU:        {cpu_color}{cpu:5.1f}%{Colors.END}  [{cpu_bar}]")

        # Memory
        mem_color = get_status_color(memory_mb, 1024, 1536)
        mem_bar = '█' * int(min(memory_mb / 20, 50)) + '░' * (50 - int(min(memory_mb / 20, 50)))
        print(f"  Memory:     {mem_color}{format_size(memory_mb):>8}{Colors.END}  [{mem_bar}]")

        # Files
        files_color = get_status_color(open_files, 500, 1000)
        print(f"  Open Files: {files_color}{open_files:4d}{Colors.END}")

        # Threads
        print(f"  Threads:    {Colors.CYAN}{threads:4d}{Colors.END}")

        # Network Connections
        print(f"  Net Conns:  {Colors.CYAN}{connections:4d}{Colors.END}")

    # Health indicators
    print(f"\n{Colors.BOLD}🏥 Health Status:{Colors.END}")

    health_items = []

    # Check connection capacity
    if total_conns < 50:
        health_items.append((f"{Colors.GREEN}✅ Low load{Colors.END}", "< 50 connections"))
    elif total_conns < 150:
        health_items.append((f"{Colors.YELLOW}⚠️  Medium load{Colors.END}", f"{total_conns} connections"))
    elif total_conns < 250:
        health_items.append((f"{Colors.YELLOW}⚠️  High load{Colors.END}", f"{total_conns} connections"))
    else:
        health_items.append((f"{Colors.RED}🔥 Very high load{Colors.END}", f"{total_conns} connections - consider Redis!"))

    # Check CPU
    if system:
        if cpu < 70:
            health_items.append((f"{Colors.GREEN}✅ CPU normal{Colors.END}", f"{cpu:.1f}%"))
        elif cpu < 90:
            health_items.append((f"{Colors.YELLOW}⚠️  CPU high{Colors.END}", f"{cpu:.1f}%"))
        else:
            health_items.append((f"{Colors.RED}❌ CPU critical{Colors.END}", f"{cpu:.1f}%"))

        # Check Memory
        if memory_mb < 1024:
            health_items.append((f"{Colors.GREEN}✅ Memory OK{Colors.END}", format_size(memory_mb)))
        elif memory_mb < 1536:
            health_items.append((f"{Colors.YELLOW}⚠️  Memory high{Colors.END}", format_size(memory_mb)))
        else:
            health_items.append((f"{Colors.RED}❌ Memory critical{Colors.END}", format_size(memory_mb)))

    for status, detail in health_items:
        print(f"  {status:<50} ({detail})")

    # Footer
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}Press Ctrl+C to exit{Colors.END}")


async def monitor_loop(api_url: str, interval: int, compact: bool):
    """Main monitoring loop"""
    previous_stats = None

    try:
        while True:
            if not compact:
                clear_screen()

            stats = await fetch_stats(api_url)

            if stats:
                display_stats(stats, previous_stats)
                previous_stats = stats

            await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Monitoring stopped{Colors.END}")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Real-time system monitor for voting system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor local server (refresh every 2 seconds)
  python monitor.py --api http://localhost:2014 --interval 2

  # Monitor production server
  python monitor.py --api http://213.230.97.43:2014

  # Compact mode (no screen clear)
  python monitor.py --api http://localhost:2014 --compact
        """
    )

    parser.add_argument('--api', default='http://localhost:2014',
                       help='API URL (default: http://localhost:2014)')
    parser.add_argument('--interval', type=int, default=3,
                       help='Update interval in seconds (default: 3)')
    parser.add_argument('--compact', action='store_true',
                       help='Compact mode (no screen clearing)')

    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.CYAN}Starting monitor...{Colors.END}")
    print(f"API: {args.api}")
    print(f"Interval: {args.interval}s\n")

    try:
        asyncio.run(monitor_loop(args.api, args.interval, args.compact))
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped{Colors.END}")
        sys.exit(0)


if __name__ == '__main__':
    main()
