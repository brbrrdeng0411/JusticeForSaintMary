"""Smoke test for JusticeForSaintMary v0.2; run: python tests/smoke_playwright.py
Requires: pip install playwright; playwright install chromium
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
PATHS = [
 (["shot","reload","r_open","r_hold","r_chain","r_finish"],
  ["r_hold","r_chain","r_finish","r_open","reload","r_finish","r_chain","r_hold","r_finish","r_chain","r_hold","shot"]),
 (["p_pray","p_chain","p_lock","p_finish","r_open","r_finish"],
  ["p_lock","p_pray","p_chain","r_open","p_pray","p_chain","r_finish","p_lock","r_open","p_pray","r_finish","p_finish"]),
 (["s_guard","s_flow","s_double","s_finish","r_open","r_finish"],
  ["s_flow","s_guard","s_double","r_finish","s_guard","s_double","r_open","r_finish","s_finish","r_finish","r_open","s_flow"]),
 (["d_keep","d_gather","d_strong","d_finish","r_open","r_finish"],
  ["d_strong","d_keep","d_gather","r_open","d_finish","d_strong","r_finish","d_keep","d_gather","d_finish","r_open","r_finish"]),
]
GOALS = [32000,45000,55000,70000]

def deck_to(page, wanted):
    for slot, card in enumerate(wanted):
        current = page.evaluate("JFSM_TEST.getSave().deck")
        if current[slot] == card:
            continue
        page.locator(f'[data-slot="{slot}"]').click()
        page.locator(f'[data-pick="{card}"]').click()
    assert page.evaluate("JFSM_TEST.getSave().deck") == wanted

def play_stage(page, stage):
    wanted, actions = PATHS[stage]
    deck_to(page, wanted)
    page.locator("#start").click()
    for turn, chosen in enumerate(actions, 1):
        assert page.locator("[data-play]").count() == 3, (stage, turn)
        assert chosen in page.locator("[data-play]").evaluate_all("(els)=>els.map(x=>x.dataset.play)")
        page.locator(f'[data-play="{chosen}"]').click()
    assert page.locator("#claim").count() == 1
    score = int(page.locator(".score").last.inner_text().replace(",", ""))
    assert score >= GOALS[stage], (stage, score)
    page.locator("#claim").click()
    return score

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width":390,"height":844},accept_downloads=True)
    # The remote test sandbox can block file://; this shim exercises save serialization.
    page.add_init_script("""window.localStorage={_d:{},getItem(k){return this._d[k]??null},setItem(k,v){this._d[k]=v},removeItem(k){delete this._d[k]}}""")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(HTML, wait_until="load")
    assert page.locator("#start").count() == 1
    assert page.evaluate("JFSM_TEST.getSave().heroes") == ["rapi"]
    first_scores = []
    for run in range(3):
        if run:
            page.locator('[data-hero="rapi"]').click()
        for stage in range(4):
            score = play_stage(page, stage)
            if not run:
                first_scores.append(score)
        options = page.locator("[data-reward]").evaluate_all("(els)=>els.map(e=>e.dataset.reward)")
        assert len(options) == 3-run
        page.locator(f'[data-reward="{options[0]}"]').click()
        assert page.evaluate("JFSM_TEST.getSave().runs") == run+1
    assert page.evaluate("JFSM_TEST.getSave().heroes.length") == 4
    page.locator('[data-tab="lab"]').click()
    page.locator('[name="name"]').fill("Test Card")
    page.locator('[name="value"]').fill("777")
    page.locator('#card-form button[type="submit"]').click()
    assert page.evaluate("JFSM_TEST.getSave().custom.length") == 1
    page.locator('#lab-batch').click()
    assert page.locator(".kpi").count() == 3
    for width in (320,390,520,1280):
        page.set_viewport_size({"width":width,"height":844})
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    assert not errors, errors
    print("PASS: 3 runs, 4 characters unlocked, 12-turn manual draw, lab card, responsive UI")
    print("First run scores:", first_scores)
    browser.close()
