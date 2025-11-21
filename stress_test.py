#!/usr/bin/env python3
"""
Voting System Stress Test Tool
Tests WebSocket connections, voting load, and system performance
"""

import asyncio
import websockets
import json
import time
import sys
import argparse
import statistics
from datetime import datetime
from typing import List, Dict
import aiohttp
from collections import defaultdict

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

class StressTestResult:
    def __init__(self):
        self.total_connections = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.total_votes = 0
        self.successful_votes = 0
        self.failed_votes = 0
        self.connection_times = []
        self.vote_times = []
        self.errors = defaultdict(int)
        self.start_time = None
        self.end_time = None

    def add_connection_success(self, duration: float):
        self.total_connections += 1
        self.successful_connections += 1
        self.connection_times.append(duration)

    def add_connection_failure(self, error: str):
        self.total_connections += 1
        self.failed_connections += 1
        self.errors[error] += 1

    def add_vote_success(self, duration: float):
        self.total_votes += 1
        self.successful_votes += 1
        self.vote_times.append(duration)

    def add_vote_failure(self, error: str):
        self.total_votes += 1
        self.failed_votes += 1
        self.errors[error] += 1

    def print_summary(self):
        duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0

        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}STRESS TEST NATIJALAR{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

        # Connection statistics
        print(f"{Colors.BOLD}📡 CONNECTION STATISTICS:{Colors.END}")
        print(f"  Total attempts:      {self.total_connections}")
        print(f"  {Colors.GREEN}✅ Successful:{Colors.END}        {self.successful_connections} ({self._percent(self.successful_connections, self.total_connections)})")
        print(f"  {Colors.RED}❌ Failed:{Colors.END}            {self.failed_connections} ({self._percent(self.failed_connections, self.total_connections)})")

        if self.connection_times:
            print(f"\n  Connection timing:")
            print(f"    Average: {statistics.mean(self.connection_times):.3f}s")
            print(f"    Median:  {statistics.median(self.connection_times):.3f}s")
            print(f"    Min:     {min(self.connection_times):.3f}s")
            print(f"    Max:     {max(self.connection_times):.3f}s")

        # Vote statistics
        if self.total_votes > 0:
            print(f"\n{Colors.BOLD}🗳️  VOTING STATISTICS:{Colors.END}")
            print(f"  Total votes:         {self.total_votes}")
            print(f"  {Colors.GREEN}✅ Successful:{Colors.END}        {self.successful_votes} ({self._percent(self.successful_votes, self.total_votes)})")
            print(f"  {Colors.RED}❌ Failed:{Colors.END}            {self.failed_votes} ({self._percent(self.failed_votes, self.total_votes)})")

            if self.vote_times:
                print(f"\n  Vote timing:")
                print(f"    Average: {statistics.mean(self.vote_times):.3f}s")
                print(f"    Median:  {statistics.median(self.vote_times):.3f}s")
                print(f"    Min:     {min(self.vote_times):.3f}s")
                print(f"    Max:     {max(self.vote_times):.3f}s")
                print(f"    Votes/sec: {self.total_votes / duration:.2f}")

        # Performance metrics
        print(f"\n{Colors.BOLD}⚡ PERFORMANCE:{Colors.END}")
        print(f"  Test duration:       {duration:.2f}s")
        if self.total_connections > 0:
            print(f"  Connections/sec:     {self.total_connections / duration:.2f}")

        # Error summary
        if self.errors:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ ERRORS:{Colors.END}")
            for error, count in sorted(self.errors.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  [{count:3d}x] {error}")

        # Overall result
        success_rate = self._percent(self.successful_connections, self.total_connections)
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        if float(success_rate.strip('%')) >= 95:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ TEST PASSED - Success rate: {success_rate}{Colors.END}")
        elif float(success_rate.strip('%')) >= 80:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  TEST WARNING - Success rate: {success_rate}{Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ TEST FAILED - Success rate: {success_rate}{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    def _percent(self, value: int, total: int) -> str:
        if total == 0:
            return "0.00%"
        return f"{(value / total * 100):.2f}%"


async def connect_user(api_url: str, event_link: str, user_id: int, result: StressTestResult,
                       duration: int = 60, vote: bool = False) -> bool:
    """Connect a single user via WebSocket"""
    ws_url = f"ws://{api_url.replace('http://', '').replace('https://', '')}/ws/vote/{event_link}"

    start_time = time.time()

    try:
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=30) as ws:
            connection_time = time.time() - start_time
            result.add_connection_success(connection_time)

            print(f"{Colors.GREEN}✅{Colors.END} User {user_id:3d} connected ({connection_time:.3f}s)")

            # Receive initial data
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(response)

                # If voting is enabled, cast a vote
                if vote and data.get('type') == 'current_candidate':
                    candidate_data = data.get('data', {})
                    candidate = candidate_data.get('candidate')

                    if candidate:
                        # Wait a random time before voting (simulate real user behavior)
                        await asyncio.sleep(0.5)

                        vote_start = time.time()
                        vote_payload = {
                            "type": "cast_vote",
                            "vote_type": "yes",  # Always vote yes for stress test
                            "nonce": f"stress-test-{user_id}-{int(time.time())}",
                            "device_id": f"device-{user_id}"
                        }

                        await ws.send(json.dumps(vote_payload))

                        # Wait for confirmation
                        vote_response = await asyncio.wait_for(ws.recv(), timeout=5)
                        vote_data = json.loads(vote_response)

                        vote_time = time.time() - vote_start

                        if vote_data.get('type') == 'vote_confirmed':
                            result.add_vote_success(vote_time)
                            print(f"{Colors.GREEN}🗳️ {Colors.END} User {user_id:3d} voted successfully ({vote_time:.3f}s)")
                        else:
                            result.add_vote_failure(f"Vote not confirmed: {vote_data.get('type')}")
                            print(f"{Colors.RED}❌{Colors.END} User {user_id:3d} vote failed: {vote_data.get('message', 'Unknown')}")

            except asyncio.TimeoutError:
                result.add_connection_failure("Initial data timeout")
                print(f"{Colors.RED}❌{Colors.END} User {user_id:3d} timeout waiting for initial data")
                return False

            # Keep connection alive
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    # Send ping
                    await ws.send(json.dumps({"type": "ping"}))

                    # Wait for messages with timeout
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=5)
                        # Process any incoming messages
                    except asyncio.TimeoutError:
                        pass  # No message, that's ok

                    await asyncio.sleep(1)

                except Exception as e:
                    result.add_connection_failure(f"Connection lost: {type(e).__name__}")
                    print(f"{Colors.RED}❌{Colors.END} User {user_id:3d} connection lost: {e}")
                    return False

            print(f"{Colors.BLUE}👋{Colors.END} User {user_id:3d} disconnecting")
            return True

    except websockets.exceptions.InvalidStatusCode as e:
        result.add_connection_failure(f"Invalid status: {e.status_code}")
        print(f"{Colors.RED}❌{Colors.END} User {user_id:3d} connection failed: HTTP {e.status_code}")
        return False
    except ConnectionRefusedError:
        result.add_connection_failure("Connection refused")
        print(f"{Colors.RED}❌{Colors.END} User {user_id:3d} connection refused")
        return False
    except Exception as e:
        result.add_connection_failure(f"{type(e).__name__}: {str(e)[:50]}")
        print(f"{Colors.RED}❌{Colors.END} User {user_id:3d} error: {type(e).__name__}")
        return False


async def get_system_stats(api_url: str) -> Dict:
    """Get system statistics from API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/ws-stats", timeout=5) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        print(f"{Colors.YELLOW}⚠️  Failed to get stats: {e}{Colors.END}")
    return {}


async def monitor_system(api_url: str, interval: int = 5):
    """Monitor system stats during test"""
    print(f"\n{Colors.BOLD}📊 System Monitoring Started{Colors.END}")
    print(f"{Colors.BOLD}{'Time':<20} {'Connections':<15} {'CPU %':<10} {'RAM MB':<10} {'Files':<10}{Colors.END}")
    print("-" * 70)

    while True:
        stats = await get_system_stats(api_url)
        if stats:
            timestamp = datetime.now().strftime("%H:%M:%S")
            connections = stats.get('total_vote_connections', 0)
            system = stats.get('system', {})
            cpu = system.get('cpu_percent', 0)
            ram = system.get('memory_mb', 0)
            files = system.get('open_files', 0)

            print(f"{timestamp:<20} {connections:<15} {cpu:<10.1f} {ram:<10.1f} {files:<10}")

        await asyncio.sleep(interval)


async def stress_test_concurrent(api_url: str, event_link: str, num_users: int,
                                 duration: int, vote: bool, batch_size: int = 50):
    """Run stress test with concurrent connections"""
    result = StressTestResult()
    result.start_time = time.time()

    print(f"\n{Colors.BOLD}{Colors.BLUE}🚀 Starting Stress Test{Colors.END}")
    print(f"  API URL:      {api_url}")
    print(f"  Event Link:   {event_link}")
    print(f"  Users:        {num_users}")
    print(f"  Duration:     {duration}s")
    print(f"  Voting:       {vote}")
    print(f"  Batch size:   {batch_size}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    # Start monitoring in background
    monitor_task = asyncio.create_task(monitor_system(api_url))

    # Connect users in batches
    for batch_start in range(0, num_users, batch_size):
        batch_end = min(batch_start + batch_size, num_users)
        batch_num = batch_start // batch_size + 1
        total_batches = (num_users + batch_size - 1) // batch_size

        print(f"\n{Colors.BOLD}📦 Batch {batch_num}/{total_batches}: Connecting users {batch_start}-{batch_end}...{Colors.END}")

        tasks = []
        for user_id in range(batch_start, batch_end):
            task = asyncio.create_task(
                connect_user(api_url, event_link, user_id, result, duration, vote)
            )
            tasks.append(task)

        # Wait for batch to connect
        await asyncio.gather(*tasks, return_exceptions=True)

        # Small delay between batches
        if batch_end < num_users:
            print(f"{Colors.YELLOW}⏳ Waiting 2s before next batch...{Colors.END}")
            await asyncio.sleep(2)

    # Cancel monitoring
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    result.end_time = time.time()

    # Get final stats
    print(f"\n{Colors.BOLD}📊 Final System Stats:{Colors.END}")
    final_stats = await get_system_stats(api_url)
    if final_stats:
        print(json.dumps(final_stats, indent=2))

    # Print results
    result.print_summary()

    return result


async def stress_test_ramp_up(api_url: str, event_link: str, max_users: int,
                              ramp_time: int, hold_time: int, vote: bool):
    """Gradually ramp up connections"""
    result = StressTestResult()
    result.start_time = time.time()

    print(f"\n{Colors.BOLD}{Colors.BLUE}🚀 Starting Ramp-Up Test{Colors.END}")
    print(f"  Max Users:    {max_users}")
    print(f"  Ramp Time:    {ramp_time}s")
    print(f"  Hold Time:    {hold_time}s")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    # Start monitoring
    monitor_task = asyncio.create_task(monitor_system(api_url))

    tasks = []
    interval = ramp_time / max_users

    # Ramp up
    print(f"{Colors.BOLD}📈 Ramping up...{Colors.END}")
    for user_id in range(max_users):
        task = asyncio.create_task(
            connect_user(api_url, event_link, user_id, result, ramp_time + hold_time, vote)
        )
        tasks.append(task)

        if (user_id + 1) % 10 == 0:
            print(f"  {user_id + 1} users connected...")

        await asyncio.sleep(interval)

    # Hold
    print(f"\n{Colors.BOLD}⏸️  Holding at {max_users} users for {hold_time}s...{Colors.END}")
    await asyncio.sleep(hold_time)

    # Wait for all to finish
    print(f"\n{Colors.BOLD}⏳ Waiting for users to disconnect...{Colors.END}")
    await asyncio.gather(*tasks, return_exceptions=True)

    # Cancel monitoring
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    result.end_time = time.time()
    result.print_summary()

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Stress test for voting system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test 100 concurrent users for 30 seconds
  python stress_test.py --api http://localhost:2014 --link EVENT_LINK --users 100 --duration 30

  # Test with voting enabled
  python stress_test.py --api http://localhost:2014 --link EVENT_LINK --users 50 --vote

  # Ramp up to 200 users over 60 seconds, hold for 120 seconds
  python stress_test.py --api http://localhost:2014 --link EVENT_LINK --mode ramp --max-users 200 --ramp-time 60 --hold-time 120

  # Test in smaller batches (50 users at a time)
  python stress_test.py --api http://localhost:2014 --link EVENT_LINK --users 200 --batch-size 50
        """
    )

    parser.add_argument('--api', required=True, help='API URL (e.g., http://localhost:2014)')
    parser.add_argument('--link', required=True, help='Event link UUID')
    parser.add_argument('--mode', choices=['concurrent', 'ramp'], default='concurrent',
                       help='Test mode: concurrent (all at once) or ramp (gradual)')

    # Concurrent mode options
    parser.add_argument('--users', type=int, default=100, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--batch-size', type=int, default=50, help='Connect users in batches')

    # Ramp mode options
    parser.add_argument('--max-users', type=int, default=200, help='Maximum users for ramp mode')
    parser.add_argument('--ramp-time', type=int, default=60, help='Ramp up time in seconds')
    parser.add_argument('--hold-time', type=int, default=120, help='Hold time at max users')

    # Common options
    parser.add_argument('--vote', action='store_true', help='Enable voting (cast votes during test)')

    args = parser.parse_args()

    try:
        if args.mode == 'concurrent':
            asyncio.run(stress_test_concurrent(
                args.api, args.link, args.users, args.duration, args.vote, args.batch_size
            ))
        elif args.mode == 'ramp':
            asyncio.run(stress_test_ramp_up(
                args.api, args.link, args.max_users, args.ramp_time, args.hold_time, args.vote
            ))
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Test interrupted by user{Colors.END}")
        sys.exit(1)


if __name__ == '__main__':
    main()
