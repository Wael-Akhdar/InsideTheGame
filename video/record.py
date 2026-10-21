"""Record the GamePulse demo video: title cards + the real app driven by Playwright, with captions. Output: video/raw/*.webm"""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

APP = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
HERE = Path(__file__).resolve().parent
W, H = 1600, 900
CAP_JS = """([t, top]) => { let d = document.getElementById('__cap');
  if (!d) { d = document.createElement('div'); d.id='__cap'; d.className='notrans';
    d.style.cssText='position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:99999;max-width:1250px;padding:14px 26px;border-radius:14px;background:#000000d0;color:#fff;font:600 26px system-ui;text-align:center;box-shadow:0 6px 30px #0008;transition:opacity .35s';
    document.body.appendChild(d); }
  d.style.top = top ? '18px' : 'auto'; d.style.bottom = top ? 'auto' : '26px';
  d.style.opacity = t ? 1 : 0; if (t) d.textContent = t; }"""


VOICE = HERE / "voice" / "durations.json"
DUR = json.loads(VOICE.read_text()) if VOICE.exists() else {}
T0, TIMELINE, STARTED = [0.0], {}, {}


MARK_JS = """(v) => { let d = document.getElementById('__mark');
  if (!d) { d = document.createElement('div'); d.id = '__mark';
    d.style.cssText = 'position:fixed;right:0;bottom:0;width:16px;height:16px;z-index:100000';
    document.documentElement.appendChild(d); }
  d.style.background = `rgb(${v},0,255)`; }"""


def mark_value(i):
    """Colour code of voice line i: a 16 px square in the bottom-right corner that build.py finds in the recording."""
    return 30 + 16 * i


def say(page, key):
    """Start voice line `key` now: mark the frame (build.py syncs the voice on the recording itself, not on the clock)."""
    STARTED[key] = time.monotonic()
    TIMELINE[key] = round(STARTED[key] - T0[0], 2)
    page.evaluate(MARK_JS, mark_value(len(TIMELINE)))


def hold(page, key, at_least=0.0, gap=0.35):
    """Stay on the shot until voice line `key` has finished (and at least `at_least` seconds since it started)."""
    left = max(DUR.get(key, 0) + gap, at_least) - (time.monotonic() - STARTED[key])
    if left > 0:
        page.wait_for_timeout(int(left * 1000))


def cap(page, text, top=False):
    page.evaluate(CAP_JS, [text, top])


def card(page, name, secs):
    page.goto(f"file://{HERE / 'card.html'}#{name}")
    page.reload()
    say(page, name)
    hold(page, name, secs)


def typeit(page, sel, text):
    page.click(sel)
    page.fill(sel, "")
    page.type(sel, text, delay=28)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(HERE / "raw"), record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        T0[0] = time.monotonic()
        card(page, "title", 4.0)
        card(page, "problem", 4.5)

        # --- live match
        page.goto(f"{APP}/?lang=en")
        page.wait_for_selector("#mHomeLvl option", state="attached")
        page.evaluate("document.body.style.zoom = 0.8")
        page.fill("#mSeed", "15")
        page.select_option("#mSpeed", "400")
        cap(page, "Live match: 22 players, live charts, and agents that explain what the TV does not show")
        page.click("#go")
        say(page, "live")
        hold(page, "live", 9.0)
        page.mouse.wheel(0, 650)
        cap(page, "Every insight explains why it matters, cites its events, and is exported as overlay JSON")
        say(page, "insight")
        hold(page, "insight", 5.0)
        page.evaluate("window.scrollTo(0, 0)")
        cap(page, "Switch language mid-match: the whole app follows, the AI writes in French, Spanish or Arabic")
        page.select_option("#mLang", "fr")
        say(page, "lang")
        page.wait_for_timeout(4500)
        page.mouse.wheel(0, 650)
        hold(page, "lang", 9.0)
        page.select_option("#mLang", "en")
        page.wait_for_timeout(800)
        # --- ask the analyst
        page.evaluate("document.getElementById('aQ').scrollIntoView({block:'center'})")
        cap(page, "Ask the match analyst: an agent calls the engine's tools, and every number is fact-checked", top=True)
        say(page, "analyst")
        typeit(page, "#aQ", "Who is on top, and what were the key moments?")
        page.click("#aBtn")
        page.wait_for_selector("#aOut .trace", timeout=90000)
        page.evaluate("document.getElementById('aOut').scrollIntoView({block:'end'})")
        page.wait_for_timeout(4500)
        hold(page, "analyst")
        # --- live coaching
        page.goto(f"{APP}/?lang=en")
        page.wait_for_selector("#mHomeLvl option", state="attached")
        page.evaluate("document.body.style.zoom = 0.8")
        page.fill("#mSeed", "20")
        page.select_option("#mSpeed", "30")
        page.click("#go")
        page.wait_for_timeout(2500)
        page.evaluate("document.getElementById('lcScn').scrollIntoView({block:'center'})")
        cap(page, "Coach live: describe what happens, the AI turns it into rules for the simulator")
        say(page, "coachlive")
        typeit(page, "#lcScn", "The opponent gets a red card, and we go all out attack")
        page.click("#lcScnBtn")
        page.wait_for_selector("#lcOut .okb, #lcOut .offb", timeout=60000)
        page.evaluate("document.getElementById('lcOut').scrollIntoView({block:'center'})")
        page.wait_for_timeout(3500)
        hold(page, "coachlive")
        page.click("#stop")
        # --- lab + coach
        page.goto(f"{APP}/?lang=en")
        page.wait_for_selector("#lLvl option", state="attached")
        page.evaluate("document.body.style.zoom = 0.8")
        page.click("[data-tab=lab]")
        page.select_option("#lTactic", "Possession 4-3-3")
        page.select_option("#lLvl", "title")
        page.select_option("#lOppLvl", "mid")
        cap(page, "Tactic Lab: test a tactic against every style, choose your level and the opponent's, run the matches")
        say(page, "lab")
        page.click("#lRun")
        page.wait_for_selector("#lOut .lab, #lOut table", timeout=180000)
        page.wait_for_timeout(3000)
        hold(page, "lab")
        cap(page, "Ask the tactics coach: it answers by running simulations, with the numbers to prove it", top=True)
        say(page, "coach")
        typeit(page, "#cQ", "How do we do against a Low block 5-3-2 of a title contender?")
        page.click("#cBtn")
        page.wait_for_selector("#cOut .trace", timeout=120000)
        page.wait_for_timeout(4500)
        hold(page, "coach")
        # --- realism
        page.click("[data-tab=real]")
        page.wait_for_selector(".kpi")
        cap(page, "Trust: the simulator is validated against 1,446 real matches and real tracking data")
        say(page, "realism")
        page.wait_for_timeout(4000)
        page.mouse.wheel(0, 500)
        hold(page, "realism")
        page.click("#rMet .chip[data-m=pass_share]")
        cap(page, "A stronger team plays like a stronger team: real leagues (green) vs simulator (pink)")
        say(page, "strength")
        hold(page, "strength", 4.5)
        cap(page, "")
        card(page, "arch", 8.5)
        card(page, "end", 4.5)
        ctx.close()
        (HERE / "raw" / "timeline.json").write_text(json.dumps(TIMELINE, indent=1))
        b.close()


if __name__ == "__main__":
    main()
