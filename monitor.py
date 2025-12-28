import json
import os
import time
from playwright.sync_api import sync_playwright

from notifier import DiscordNotifier

def load_cookies_from_file():
    file_path = "cookies.json"

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return []

    with open(file_path, 'r') as f:
        raw_cookies = json.load(f)

    playwright_cookies = []
    for c in raw_cookies:
        samesite = str(c.get("sameSite", "Lax")).lower()
        if "no_restriction" in samesite or "none" in samesite:
            samesite = "None"
        elif "strict" in samesite:
            samesite = "Strict"
        else:
            samesite = "Lax"

        playwright_cookies.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
            "sameSite": samesite,
        })
    return playwright_cookies


def check_game_status(cookies):
    play_url = "https://www.nutaku.net/games/kamihime-r/play"
    
    with sync_playwright() as p:
        # This allows the script to read text inside cross-domain iframes
        browser = p.chromium.launch(
            headless=True, 
            args=["--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"]
        )
        
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            page.goto(play_url, wait_until="networkidle")

            game_frame = None
            for frame in page.frames:
                if "nutaku" not in frame.url and frame.url != "about:blank":
                    game_frame = frame
                    break
            
            if not game_frame:
                game_frame = page.main_frame.child_frames[0] if page.main_frame.child_frames else None

            if game_frame:
                print(f"Frame: {game_frame.url}")

                game_frame.wait_for_selector("body", timeout=15000)
                body_text = game_frame.inner_text("title").lower()
                
                maintenance_keywords = ["maintenance", "temporarily unavailable", "update"]
                is_maintenance = any(k in body_text for k in maintenance_keywords)
                
                browser.close()
                return is_maintenance, body_text[:500]
            
            return False, "No game frame detected."

        except Exception as e:
            page.screenshot(path="final_debug.png")
            browser.close()
            return False, f"Error: {str(e)}"

def run_action_check():
    webhook = os.getenv("DISCORD_WEBHOOK")
    notifier = DiscordNotifier(webhook)
    
    cookies = load_cookies_from_file()
    current_is_maintenance = check_game_status(cookies) 
    
    current_status_str = "down" if current_is_maintenance else "up"
    
    status_file = "last_status.txt"
    last_status = None
    if os.path.exists(status_file):
        with open(status_file, "r") as f:
            last_status = f.read().strip()

    if current_status_str != last_status:
        notifier.alert_status_change(current_is_maintenance)
        
        with open(status_file, "w") as f:
            f.write(current_status_str)
        print(f"Status changed from {last_status} to {current_status_str}. Notified Discord.")
    else:
        print(f"No change. Game is still {current_status_str}. Skipping notification.")

if __name__ == "__main__":
    run_action_check()