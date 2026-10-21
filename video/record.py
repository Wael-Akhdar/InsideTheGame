"""Record the GamePulse demo video: title cards + the real app driven by Playwright, with captions. Output: video/raw/*.webm"""
import sys, time
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


def cap(page, text, top=False):
    page.evaluate(CAP_JS, [text, top])


def card(page, name, secs):
    page.goto(f"file://{HERE / 'card.html'}#{name}")
    page.reload()
    page.wait_for_timeout(int(secs * 1000))


def typeit(page, sel, text):
    page.click(sel)
    page.fill(sel, "")
    page.type(sel, text, delay=28)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(HERE / "raw"), record_video_size={"width": W, "height": H})
        page = ctx.new_page()
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
        page.wait_for_timeout(9000)
        page.mouse.wheel(0, 650)
        cap(page, "Every insight explains why it matters, and cites the events behind it")
        page.wait_for_timeout(5000)
        page.evaluate("window.scrollTo(0, 0)")
        cap(page, "Switch language mid-match: the whole app follows, the AI writes in French, Spanish or Arabic")
        page.select_option("#mLang", "fr")
        page.wait_for_timeout(5500)
        page.mouse.wheel(0, 650)
        page.wait_for_timeout(5500)
        page.select_option("#mLang", "en")
        page.wait_for_timeout(1500)
        # --- ask the analyst
        page.evaluate("document.getElementById('aQ').scrollIntoView({block:'center'})")
        cap(page, "Ask the match analyst: an agent calls the engine's tools, and every number is fact-checked", top=True)
        typeit(page, "#aQ", "Who is on top, and what were the key moments?")
        page.click("#aBtn")
        page.wait_for_selector("#aOut .trace", timeout=90000)
        page.evaluate("document.getElementById('aOut').scrollIntoView({block:'end'})")
        page.wait_for_timeout(6000)
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
        typeit(page, "#lcScn", "The opponent gets a red card, and we go all out attack")
        page.click("#lcScnBtn")
        page.wait_for_selector("#lcOut .okb, #lcOut .offb", timeout=60000)
        page.evaluate("document.getElementById('lcOut').scrollIntoView({block:'center'})")
        page.wait_for_timeout(5500)
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
        page.click("#lRun")
        page.wait_for_selector("#lOut .lab, #lOut table", timeout=180000)
        page.wait_for_timeout(5000)
        cap(page, "Ask the tactics coach: it answers by running simulations, with the numbers to prove it", top=True)
        typeit(page, "#cQ", "How do we do against a Low block 5-3-2 of a title contender?")
        page.click("#cBtn")
        page.wait_for_selector("#cOut .trace", timeout=120000)
        page.wait_for_timeout(6500)
        # --- realism
        page.click("[data-tab=real]")
        page.wait_for_selector(".kpi")
        cap(page, "Trust: the simulator is validated against 1,446 real matches and real tracking data")
        page.wait_for_timeout(4000)
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(1200)
        page.click("#rMet .chip[data-m=pass_share]")
        cap(page, "A stronger team plays like a stronger team: real leagues (green) vs simulator (pink)")
        page.wait_for_timeout(5000)
        cap(page, "")
        card(page, "arch", 8.5)
        card(page, "end", 4.5)
        ctx.close()
        b.close()


if __name__ == "__main__":
    main()
