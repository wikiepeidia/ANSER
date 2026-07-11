"""Chụp channel Discord web làm evidence demo (cần trình duyệt đã đăng nhập Discord).

Thử lần lượt profile Edge rồi Chrome của user (persistent context — giữ session đăng nhập).
Nếu trình duyệt đang mở khóa profile → đóng trình duyệt rồi chạy lại, hoặc chụp tay.
"""
import sys
import time
from pathlib import Path

CHANNEL_URL = "https://discord.com/channels/1493147638017818634/1512466061369409728"
OUT = Path(__file__).resolve().parents[2] / "tests" / "evidence" / "discord_real.png"

PROFILES = [
    ("msedge", Path.home() / "AppData/Local/Microsoft/Edge/User Data"),
    ("chrome", Path.home() / "AppData/Local/Google/Chrome/User Data"),
]


def main():
    from playwright.sync_api import sync_playwright
    for channel, profile in PROFILES:
        if not profile.exists():
            continue
        try:
            with sync_playwright() as p:
                ctx = p.chromium.launch_persistent_context(
                    str(profile), channel=channel, headless=False,
                    viewport={"width": 1400, "height": 900},
                    args=["--profile-directory=Default"])
                page = ctx.new_page()
                page.goto(CHANNEL_URL, wait_until="domcontentloaded", timeout=45000)
                time.sleep(12)  # chờ app Discord render + tải tin nhắn
                if "login" in page.url:
                    print(f"[{channel}] profile chưa đăng nhập Discord — bỏ qua")
                    ctx.close()
                    continue
                page.screenshot(path=str(OUT))
                ctx.close()
                print(f"OK: đã chụp bằng {channel} → {OUT}")
                return 0
        except Exception as e:
            print(f"[{channel}] không dùng được profile ({type(e).__name__}): {str(e)[:150]}")
    print("Không chụp tự động được (trình duyệt đang mở khóa profile hoặc chưa đăng nhập).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
