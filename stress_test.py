"""
Stress test for the voting system.

Simulates real voting flow:
1. Admin logs in and starts timer
2. Users connect via WebSocket and vote
3. Timer expires → admin moves to next candidate
4. Repeat for all candidates

Usage:
    pip install websockets aiohttp

    # 50 users, auto admin flow
    python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 50

    # 200 users
    python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 200

    # 500 users with custom timer
    python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 500 --timer 30

    # Only voters (admin manages manually)
    python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 200 --no-admin
"""

import asyncio
import argparse
import json
import time
import random
import uuid
import sys
from dataclasses import dataclass, field
from typing import Optional

try:
    import websockets
except ImportError:
    print("Install: pip install websockets")
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    print("Install: pip install aiohttp")
    sys.exit(1)


@dataclass
class Stats:
    total_users: int = 0
    connected: int = 0
    failed_connections: int = 0
    messages_received: int = 0
    votes_sent: int = 0
    votes_confirmed: int = 0
    votes_rejected: int = 0
    duplicate_votes: int = 0
    errors: int = 0
    candidates_voted: int = 0
    connect_times: list = field(default_factory=list)
    vote_latencies: list = field(default_factory=list)
    connection_errors: list = field(default_factory=list)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def inc(self, attr: str, value: int = 1):
        async with self._lock:
            setattr(self, attr, getattr(self, attr) + value)

    async def append_to(self, attr: str, value):
        async with self._lock:
            getattr(self, attr).append(value)

    def summary(self):
        avg_connect = sum(self.connect_times) / len(self.connect_times) if self.connect_times else 0
        max_connect = max(self.connect_times) if self.connect_times else 0
        min_connect = min(self.connect_times) if self.connect_times else 0
        p95_connect = sorted(self.connect_times)[int(len(self.connect_times) * 0.95)] if self.connect_times else 0

        avg_vote_lat = sum(self.vote_latencies) / len(self.vote_latencies) if self.vote_latencies else 0
        max_vote_lat = max(self.vote_latencies) if self.vote_latencies else 0
        p95_vote_lat = sorted(self.vote_latencies)[int(len(self.vote_latencies) * 0.95)] if self.vote_latencies else 0

        print("\n" + "=" * 60)
        print("STRESS TEST NATIJALARI")
        print("=" * 60)

        print(f"\n--- Ulanishlar ---")
        print(f"  {'Jami foydalanuvchilar':<30} {self.total_users}")
        print(f"  {'Muvaffaqiyatli':<30} {self.connected}")
        print(f"  {'Muvaffaqiyatsiz':<30} {self.failed_connections}")
        success_rate = self.connected / self.total_users * 100 if self.total_users else 0
        print(f"  {'Ulanish darajasi':<30} {success_rate:.1f}%")

        print(f"\n--- Ulanish vaqti ---")
        print(f"  {'O`rtacha':<30} {avg_connect * 1000:.0f} ms")
        print(f"  {'Minimal':<30} {min_connect * 1000:.0f} ms")
        print(f"  {'Maksimal':<30} {max_connect * 1000:.0f} ms")
        print(f"  {'95-persentil':<30} {p95_connect * 1000:.0f} ms")

        print(f"\n--- Ovoz berish ---")
        print(f"  {'Yuborilgan ovozlar':<30} {self.votes_sent}")
        print(f"  {'Tasdiqlangan':<30} {self.votes_confirmed}")
        print(f"  {'Rad etilgan':<30} {self.votes_rejected}")
        print(f"  {'Takroriy (duplicate)':<30} {self.duplicate_votes}")
        print(f"  {'Kandidatlar soni':<30} {self.candidates_voted}")

        if self.vote_latencies:
            print(f"\n--- Ovoz berish vaqti ---")
            print(f"  {'O`rtacha':<30} {avg_vote_lat * 1000:.0f} ms")
            print(f"  {'Maksimal':<30} {max_vote_lat * 1000:.0f} ms")
            print(f"  {'95-persentil':<30} {p95_vote_lat * 1000:.0f} ms")

        print(f"\n--- Umumiy ---")
        print(f"  {'Qabul qilingan xabarlar':<30} {self.messages_received}")
        print(f"  {'Xatolar':<30} {self.errors}")

        if self.connection_errors:
            print(f"\n--- Xato turlari ---")
            error_counts = {}
            for err in self.connection_errors:
                err_str = str(err)[:80]
                error_counts[err_str] = error_counts.get(err_str, 0) + 1
            for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"  [{count}x] {err}")

        print("\n" + "=" * 60)
        if success_rate >= 99 and avg_connect < 1:
            print("NATIJA: AJOYIB - Tizim barqaror ishlaydi")
        elif success_rate >= 95 and avg_connect < 2:
            print("NATIJA: YAXSHI - Tizim yetarli darajada ishlaydi")
        elif success_rate >= 80:
            print("NATIJA: QONIQARLI - Ba'zi muammolar bor")
        else:
            print("NATIJA: YOMON - Tizimni optimallashtirish kerak")
        print("=" * 60)


stats = Stats()


class AdminBot:
    """Admin sifatida login qilib, timer boshlash va keyingi kandidatga o'tish."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url
        self.username = username
        self.password = password
        self.token = None
        self.session = None

    async def login(self):
        self.session = aiohttp.ClientSession()
        async with self.session.post(
            f"{self.api_url}/auth/login",
            json={"username": self.username, "password": self.password},
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Admin login failed: {resp.status} {text}")
            data = await resp.json()
            self.token = data["access_token"]
            print(f"  Admin login muvaffaqiyatli")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def get_event_by_link(self, link: str) -> dict:
        async with self.session.get(
            f"{self.api_url}/events/by-link/{link}",
            headers=self._headers(),
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Event not found: {resp.status}")
            return await resp.json()

    async def start_timer(self, event_id: int, duration_sec: int = None):
        body = {}
        if duration_sec:
            body["duration_sec"] = duration_sec
        async with self.session.post(
            f"{self.api_url}/event-management/{event_id}/start-timer",
            json=body,
            headers=self._headers(),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"  Timer xato: {resp.status} {text[:100]}")
                return False
            return True

    async def next_candidate(self, event_id: int):
        async with self.session.post(
            f"{self.api_url}/event-management/{event_id}/next-candidate",
            headers=self._headers(),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"  Next candidate xato: {resp.status} {text[:100]}")
                return False
            return True

    async def get_current_candidate(self, event_id: int):
        async with self.session.get(
            f"{self.api_url}/event-management/{event_id}/current-candidate",
            headers=self._headers(),
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

    async def close(self):
        if self.session:
            await self.session.close()


async def simulate_voter(
    ws_url: str,
    link: str,
    user_id: int,
    semaphore: asyncio.Semaphore,
    stop_event: asyncio.Event,
    vote_delay_range: tuple = (0.5, 3.0),
):
    """Bitta ovoz beruvchi — ulanib turadi, har yangi kandidatga ovoz beradi."""
    async with semaphore:
        ws_full_url = f"{ws_url}/ws/vote/{link}"
        device_id = str(uuid.uuid4())

        # Origin header
        origin = ws_url.replace("ws://", "http://").replace("wss://", "https://")
        parts = origin.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            web_port = int(parts[1]) - 1
            origin = f"{parts[0]}:{web_port}"

        start_time = time.time()
        current_candidate_id = None
        voted_candidates = set()

        try:
            async with websockets.connect(
                ws_full_url,
                open_timeout=30,
                ping_interval=None,
                ping_timeout=None,
                additional_headers={
                    "Origin": origin,
                    "X-Forwarded-For": f"10.0.{user_id // 256}.{user_id % 256}",
                },
            ) as ws:
                connect_time = time.time() - start_time
                await stats.append_to("connect_times", connect_time)
                await stats.inc("connected")

                connected_count = stats.connected
                if connected_count % 50 == 0:
                    print(f"  [{connected_count}/{stats.total_users}] ulanish muvaffaqiyatli...")

                # Ovoz berish uchun alohida asyncio.Event — xabar loop bloklanmaydi
                vote_trigger = asyncio.Event()
                pending_vote_candidate = None
                vote_attempted = set()  # Ovoz yuborish boshlangan kandidatlar

                async def receive_loop():
                    """Faqat xabarlarni qabul qiladi — hech qachon bloklanmaydi."""
                    nonlocal current_candidate_id, pending_vote_candidate
                    try:
                        async for message in ws:
                            await stats.inc("messages_received")
                            try:
                                data = json.loads(message)
                            except json.JSONDecodeError:
                                continue

                            msg_type = data.get("type")

                            if msg_type == "current_candidate":
                                cand_data = data.get("data")
                                if cand_data and cand_data.get("candidate"):
                                    new_id = cand_data["candidate"]["id"]
                                    timer = cand_data.get("timer", {})
                                    timer_running = timer.get("running", False)
                                    remaining = timer.get("remaining_ms", 0)

                                    if new_id != current_candidate_id:
                                        current_candidate_id = new_id

                                    # Ovoz berish kerakligini signal qilish (bloklamasdan)
                                    if (timer_running and remaining > 1000
                                            and new_id not in voted_candidates
                                            and new_id not in vote_attempted):
                                        pending_vote_candidate = new_id
                                        vote_trigger.set()

                                elif not cand_data or not cand_data.get("candidate"):
                                    idx = (cand_data or {}).get("index", 0)
                                    total = (cand_data or {}).get("total", 0)
                                    if total > 0 and idx >= total:
                                        return  # Event tugadi

                            elif msg_type == "vote_confirmed":
                                await stats.inc("votes_confirmed")
                                cand_id = data.get("candidate_id")
                                if cand_id:
                                    voted_candidates.add(cand_id)
                                    await stats.inc("candidates_voted")

                            elif msg_type == "error":
                                err_msg = data.get("message", "")
                                if "allaqachon" in err_msg:
                                    await stats.inc("duplicate_votes")
                                else:
                                    await stats.inc("votes_rejected")

                    except websockets.exceptions.ConnectionClosed:
                        pass
                    except Exception:
                        pass

                async def vote_loop():
                    """Alohida loop — signal kelganda ovoz beradi."""
                    nonlocal pending_vote_candidate
                    try:
                        while not stop_event.is_set():
                            vote_trigger.clear()
                            await vote_trigger.wait()

                            cand_id = pending_vote_candidate
                            if not cand_id or cand_id in voted_candidates or cand_id in vote_attempted:
                                continue

                            vote_attempted.add(cand_id)

                            # Random kutish
                            delay = random.uniform(*vote_delay_range)
                            await asyncio.sleep(delay)

                            # Hali ham aktiv ekanligini tekshirish
                            if cand_id in voted_candidates:
                                continue

                            vote_type = random.choice(["yes", "no", "neutral"])
                            nonce = str(uuid.uuid4())
                            vote_msg = {
                                "type": "cast_vote",
                                "vote_type": vote_type,
                                "nonce": nonce,
                                "device_id": device_id,
                                "candidate_id": cand_id,
                            }
                            try:
                                await ws.send(json.dumps(vote_msg))
                                await stats.inc("votes_sent")
                            except Exception:
                                break
                    except asyncio.CancelledError:
                        pass

                async def ping_loop():
                    try:
                        while not stop_event.is_set():
                            await asyncio.sleep(15)
                            try:
                                await ws.send(json.dumps({"type": "ping"}))
                            except Exception:
                                break
                    except asyncio.CancelledError:
                        pass

                receive_task = asyncio.create_task(receive_loop())
                vote_task = asyncio.create_task(vote_loop())
                ping_task = asyncio.create_task(ping_loop())

                # stop_event kutish yoki receive tugashini kutish
                done, pending = await asyncio.wait(
                    [receive_task, asyncio.create_task(stop_event.wait())],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in [vote_task, ping_task, *pending]:
                    if not task.done():
                        task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            await stats.inc("failed_connections")
            await stats.inc("errors")
            await stats.append_to("connection_errors", e)


async def admin_flow(
    admin: AdminBot,
    event_id: int,
    timer_duration: int,
    wait_after_timer: int,
    stop_event: asyncio.Event,
):
    """Admin sifatida timer boshlash va kandidatlarni boshqarish."""
    candidate_num = 0
    while not stop_event.is_set():
        candidate_num += 1

        # Joriy kandidatni tekshirish
        current = await admin.get_current_candidate(event_id)
        if not current or not current.get("candidate"):
            print(f"\n  Admin: Barcha kandidatlar tugadi!")
            stop_event.set()
            break

        cand_name = current["candidate"].get("full_name", "Noma'lum")
        idx = current.get("index", 0) + 1
        total = current.get("total", 0)
        timer = current.get("timer", {})

        # Agar timer allaqachon ishlayotgan bo'lsa, kutamiz
        if timer.get("running") and timer.get("remaining_ms", 0) > 0:
            remaining_sec = timer["remaining_ms"] / 1000
            print(f"\n  Admin: Kandidat {idx}/{total}: {cand_name} — timer ishlayapti ({remaining_sec:.0f}s qoldi)")
            await asyncio.sleep(remaining_sec + 1)
        else:
            # Timer boshlash
            print(f"\n  Admin: Kandidat {idx}/{total}: {cand_name} — timer boshlanmoqda ({timer_duration}s)...")
            success = await admin.start_timer(event_id, timer_duration)
            if not success:
                print(f"  Admin: Timer boshlanmadi, 3s kutilmoqda...")
                await asyncio.sleep(3)
                continue

            # Timer tugashini kutish
            await asyncio.sleep(timer_duration + 1)

        # Timer tugagandan keyin qisqa pauza
        print(f"  Admin: Timer tugadi. {wait_after_timer}s kutilmoqda...")
        await asyncio.sleep(wait_after_timer)

        # Keyingi kandidatga o'tish
        print(f"  Admin: Keyingi kandidatga o'tilmoqda...")
        success = await admin.next_candidate(event_id)
        if not success:
            print(f"  Admin: Keyingi kandidatga o'tib bo'lmadi. Event tugagan bo'lishi mumkin.")
            # Tekshirish
            current = await admin.get_current_candidate(event_id)
            if not current or not current.get("candidate"):
                stop_event.set()
                break
            await asyncio.sleep(2)

        # Kandidatlar o'rtasida qisqa pauza
        await asyncio.sleep(1)


async def run_stress_test(args):
    stats.total_users = args.users
    http_url = args.url
    ws_url = http_url.replace("http://", "ws://").replace("https://", "wss://")
    link = args.link

    max_concurrent = min(args.users, args.max_concurrent)
    semaphore = asyncio.Semaphore(max_concurrent)
    stop_event = asyncio.Event()

    print("=" * 60)
    print("OVOZ BERISH TIZIMI STRESS TEST")
    print("=" * 60)
    print(f"  Server: {http_url}")
    print(f"  Event link: {link}")
    print(f"  Foydalanuvchilar: {args.users}")
    print(f"  Bir vaqtda maks: {max_concurrent}")
    print(f"  Admin boshqaruvi: {'Ha' if not args.no_admin else 'Yo`q (qo`lda boshqarish)'}")
    if not args.no_admin:
        print(f"  Timer davomiyligi: {args.timer}s")
        print(f"  Kandidatlar orasidagi pauza: {args.pause}s")
    print()

    # Admin login
    admin = None
    event_id = None
    if not args.no_admin:
        print("--- Admin login ---")
        admin = AdminBot(http_url, args.admin_user, args.admin_pass)
        try:
            await admin.login()
            event_data = await admin.get_event_by_link(link)
            event_id = event_data["id"]
            print(f"  Event ID: {event_id}")
            print(f"  Event nomi: {event_data.get('name', 'N/A')}")

            # Joriy kandidatni tekshirish
            current = await admin.get_current_candidate(event_id)
            if current and current.get("candidate"):
                total = current.get("total", 0)
                idx = current.get("index", 0) + 1
                print(f"  Kandidatlar: {total} ta (hozirgi: {idx}/{total})")
            else:
                print(f"  Diqqat: Hozirda aktiv kandidat yo'q")
        except Exception as e:
            print(f"  Admin xato: {e}")
            print(f"  --no-admin rejimda davom etilmoqda...")
            args.no_admin = True
            if admin:
                await admin.close()
                admin = None

    # Foydalanuvchilarni ulash
    print(f"\n--- Foydalanuvchilarni ulash ---")
    start_time = time.time()

    batch_size = args.batch_size
    total_batches = (args.users + batch_size - 1) // batch_size

    voter_tasks = []
    for batch_num in range(total_batches):
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, args.users)
        current_batch_size = batch_end - batch_start

        print(f"  Bosqich {batch_num + 1}/{total_batches}: {current_batch_size} ta foydalanuvchi...")

        for i in range(batch_start, batch_end):
            task = asyncio.create_task(
                simulate_voter(
                    ws_url=ws_url,
                    link=link,
                    user_id=i,
                    semaphore=semaphore,
                    stop_event=stop_event,
                    vote_delay_range=(args.min_vote_delay, args.max_vote_delay),
                )
            )
            voter_tasks.append(task)
            if i % 10 == 0:
                await asyncio.sleep(0.05)

        if batch_num < total_batches - 1:
            await asyncio.sleep(args.batch_delay)

    # Ulanish tugashini biroz kutish
    connect_wait = min(5, args.users / 50)
    print(f"\n  Ulanishlarni barqarorlashtirish uchun {connect_wait:.0f}s kutilmoqda...")
    await asyncio.sleep(connect_wait)
    print(f"  Ulangan: {stats.connected}/{stats.total_users}")

    # Enter bosilsa to'xtatish uchun stdin listener
    async def wait_for_enter():
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sys.stdin.readline)
        print("\n  Enter bosildi — test to'xtatilmoqda...")
        stop_event.set()

    enter_task = asyncio.create_task(wait_for_enter())

    # Admin flow boshlash
    if not args.no_admin and admin and event_id:
        print(f"\n--- Ovoz berish boshlandi ---")
        print(f"  To'xtatish uchun Enter bosing\n")
        admin_task = asyncio.create_task(
            admin_flow(admin, event_id, args.timer, args.pause, stop_event)
        )

        # Admin, enter yoki timeout kutish
        done, pending = await asyncio.wait(
            [admin_task, enter_task],
            return_when=asyncio.FIRST_COMPLETED,
            timeout=args.timeout,
        )

        # Admin tugagandan keyin voterlarga 3s vaqt berish
        if admin_task in done and not stop_event.is_set():
            print(f"\n  Admin flow tugadi. 3s kutilmoqda...")
            await asyncio.sleep(3)

        stop_event.set()

        # Barcha tasklarni tozalash
        for task in voter_tasks:
            if not task.done():
                task.cancel()
        if not admin_task.done():
            admin_task.cancel()
        if not enter_task.done():
            enter_task.cancel()

        await asyncio.gather(*voter_tasks, admin_task, return_exceptions=True)
        await admin.close()
    else:
        # Admin yo'q — Enter yoki timeout kutish
        print(f"\n--- Admin qo'lda boshqaradi ---")
        print(f"  Ovoz berish admin tomonidan boshlanishini kutmoqda...")
        print(f"  To'xtatish uchun Enter bosing\n")

        done, pending = await asyncio.wait(
            [enter_task],
            return_when=asyncio.FIRST_COMPLETED,
            timeout=args.timeout,
        )

        if not stop_event.is_set():
            print(f"\n  Timeout ({args.timeout}s) tugadi")
            stop_event.set()

        for task in voter_tasks:
            if not task.done():
                task.cancel()
        if not enter_task.done():
            enter_task.cancel()

        await asyncio.gather(*voter_tasks, return_exceptions=True)

    total_time = time.time() - start_time

    # Natijalar
    stats.summary()
    print(f"\nUmumiy vaqt: {total_time:.1f} sek")


def main():
    parser = argparse.ArgumentParser(
        description="Ovoz berish tizimi stress test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Misollar:
  # 50 ta foydalanuvchi, avtomatik admin
  python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 50

  # 200 ta foydalanuvchi, 20 soniya timer
  python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 200 --timer 20

  # 500 ta foydalanuvchi, admin qo'lda boshqaradi
  python3 stress_test.py --url http://127.0.0.1:2012 --link 37694e2d --users 500 --no-admin

  # Production server
  python3 stress_test.py --url http://213.230.97.43:2012 --link 37694e2d --users 300
        """,
    )

    parser.add_argument("--url", required=True, help="API server URL (masalan: http://127.0.0.1:2012)")
    parser.add_argument("--link", required=True, help="Event link (UUID yoki to'liq URL)")
    parser.add_argument("--users", type=int, default=50, help="Foydalanuvchilar soni (default: 50)")
    parser.add_argument("--timer", type=int, default=15, help="Timer davomiyligi sekundlarda (default: 15)")
    parser.add_argument("--pause", type=int, default=3, help="Kandidatlar orasidagi pauza, sek (default: 3)")
    parser.add_argument("--no-admin", action="store_true", help="Admin boshqaruvini o'chirish (qo'lda boshqarish)")
    parser.add_argument("--admin-user", default="admin", help="Admin username (default: admin)")
    parser.add_argument("--admin-pass", default="admin123", help="Admin password")
    parser.add_argument("--max-concurrent", type=int, default=300, help="Bir vaqtda maks ulanishlar (default: 300)")
    parser.add_argument("--batch-size", type=int, default=50, help="Har bosqichdagi foydalanuvchilar (default: 50)")
    parser.add_argument("--batch-delay", type=float, default=1, help="Bosqichlar orasidagi kutish, sek (default: 1)")
    parser.add_argument("--min-vote-delay", type=float, default=0.5, help="Minimal ovoz berish kutishi, sek (default: 0.5)")
    parser.add_argument("--max-vote-delay", type=float, default=5.0, help="Maksimal ovoz berish kutishi, sek (default: 5.0)")
    parser.add_argument("--timeout", type=int, default=600, help="Umumiy timeout sekundlarda (default: 600)")

    args = parser.parse_args()

    # URL'dan link ajratish
    if "/" in args.link:
        args.link = args.link.rstrip("/").split("/")[-1]
        print(f"Link ajratildi: {args.link}")

    asyncio.run(run_stress_test(args))


if __name__ == "__main__":
    main()
