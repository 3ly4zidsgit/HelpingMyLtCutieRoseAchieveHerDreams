"""Last-mile pass: the offers still sitting on a Cloudflare interstitial.

Why the ordinary UC pass leaves them behind on this machine: Windows display
scaling is 150 %, so Selenium reports the checkbox position in logical pixels
(2560x1440) while PyAutoGUI clicks in physical ones (3840x2160). Every
`uc_gui_click_captcha()` lands at two thirds of the right spot and misses.

`uc_gui_handle_captcha()` drives the challenge with TAB + SPACE instead of a
mouse coordinate, so display scaling cannot throw it off. Try that first, and
only fall back to the coordinate click.

Run: python fetch_captcha.py [--shot]
"""
import sys, io, os, re, json, time, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skill", "findmyprincessajob", "pipeline"))
import fulltext as F


class Run:
    datadir = os.path.join(ROOT, "data")


CHALLENGE = F.CHALLENGE + ("verifying you are human", "verification en cours",
                           "enable javascript and cookies", "attendez")
SHOT = os.path.join(ROOT, "data", "captcha_shots")


def blocked(sb):
    try:
        src = sb.get_page_source()[:6000].lower()
        ttl = (sb.get_title() or "").lower()
    except Exception:
        return True
    return any(k in src or k in ttl for k in CHALLENGE)


def solve(sb, url, host, shot=False, rounds=4):
    sb.uc_open_with_reconnect(url, reconnect_time=6)
    for r in range(rounds):
        if not blocked(sb):
            return True
        try:
            sb.bring_active_window_to_front()
        except Exception:
            pass
        # keyboard first: immune to display scaling
        try:
            sb.uc_gui_handle_captcha()
        except Exception as e:
            print(f"      handle_captcha: {type(e).__name__}", flush=True)
            try:
                sb.uc_gui_click_captcha()
            except Exception:
                pass
        time.sleep(4 + 2 * r)
        if shot and r == 0:
            os.makedirs(SHOT, exist_ok=True)
            try:
                sb.save_screenshot(os.path.join(SHOT, f"{host}.png"))
            except Exception:
                pass
    return not blocked(sb)


def main():
    shot = "--shot" in sys.argv
    store = F._load(Run())
    walled = json.load(open(os.path.join(Run.datadir, "walled_urls.json"),
                            encoding="utf-8"))
    urls = [u for lst in walled.values() for u in lst]
    todo = [u for u in urls if not F._have(store, u)]
    print(f"{len(todo)} offres encore bloquees", flush=True)
    if not todo:
        return

    from urllib.parse import urlparse
    from seleniumbase import SB
    ok = 0
    with SB(uc=True, headless=False, page_load_strategy="eager") as sb:
        try:
            sb.maximize_window()
        except Exception:
            pass
        for i, u in enumerate(todo, 1):
            host = urlparse(u).netloc.replace("www.", "")
            try:
                cleared = solve(sb, u, host, shot=shot and i == 1)
                txt = F._extract(sb.get_page_source(), host)
                ttl = re.sub(r"\s+", " ", sb.get_title() or "").strip()
                if len(txt) >= F.MIN_BODY:
                    store[u] = {"text": txt, "title": ttl, "ok": True}
                    ok += 1
                    print(f"  {i}/{len(todo)} OK   {host} ({len(txt)} car)", flush=True)
                else:
                    print(f"  {i}/{len(todo)} {'VIDE' if cleared else 'BLOQUE'} "
                          f"{host} ({len(txt)} car) titre={ttl[:50]!r}", flush=True)
            except Exception as e:
                print(f"  {i}/{len(todo)} ERREUR {host} {type(e).__name__}", flush=True)
            if i % 5 == 0:
                F._save(Run(), store)
    F._save(Run(), store)
    print(f"TERMINE: {ok}/{len(todo)} debloquees", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
