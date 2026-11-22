"""Smoke-проверка интерфейса: вход под тремя ролями, обход основных экранов на 360 и 1280 px,
отсутствие горизонтальной прокрутки и ошибок консоли, скриншоты в docs/screenshots/.
Запуск:  python frontend/e2e/smoke.py [http://127.0.0.1:8000]   (сервер с DEMO_TODAY=2026-11-23)"""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parents[2] / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
PASSWORDS = {"student1": "student1-demo", "student2": "student2-demo", "dekanat": "dekanat-demo"}
problems: list[str] = []


def login(page, who):
    page.goto(f"{BASE}/login")
    page.locator("#login").fill(who)
    page.locator("#password").fill(PASSWORDS[who])
    page.get_by_role("button", name=re.compile("Войти")).click()
    page.wait_for_url(re.compile(r"/(staff)?$"), timeout=10000)


def check(page, name, width, shot=True):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(250)
    sw = page.evaluate("document.documentElement.scrollWidth")
    if sw > width + 1:
        problems.append(f"{name}@{width}: horizontal scroll {sw}px")
    if shot:
        page.screenshot(path=str(OUT / f"{name}-{'mobile' if width < 500 else 'desktop'}.png"), full_page=True)


def run(width, height):
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/google-chrome")
        ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=2 if width < 500 else 1)
        page = ctx.new_page()
        page.on("console", lambda m: m.type == "error" and problems.append(f"console@{width}: {m.text[:200]}"))
        page.on("pageerror", lambda e: problems.append(f"pageerror@{width}: {e}"))

        page.goto(f"{BASE}/login")
        check(page, "01-login", width)
        login(page, "student1")
        check(page, "02-home-student1", width)
        page.goto(f"{BASE}/schedule?date=2026-11-23")
        check(page, "03-schedule-day", width)
        week = page.get_by_role("button", name="Неделя")
        if week.count():
            week.first.click()
        check(page, "04-schedule-week", width)
        page.goto(f"{BASE}/study")
        check(page, "05-radar-student1", width)
        page.goto(f"{BASE}/study?tab=record")
        check(page, "06-record-book", width)
        page.goto(f"{BASE}/applications")
        check(page, "07-applications", width)
        page.goto(f"{BASE}/applications/new?type=study_certificate")
        check(page, "08-new-application", width)
        page.get_by_label("Куда предоставляется").fill("Для предоставления в банк")
        page.get_by_role("button", name="Отправить", exact=True).click()
        page.get_by_text("Заявка отправлена").wait_for(timeout=8000)
        check(page, "09-application-sent", width)
        page.get_by_role("link", name="Открыть заявку").click()
        check(page, "10-application-card", width)
        page.goto(f"{BASE}/notifications")
        check(page, "11-notifications", width)
        page.goto(f"{BASE}/profile")
        check(page, "12-profile", width)
        page.goto(f"{BASE}/help")
        check(page, "13-help", width, shot=width < 500)
        page.goto(f"{BASE}/no-such-page")
        check(page, "14-not-found", width, shot=False)
        page.goto(f"{BASE}/profile")
        page.get_by_role("button", name="Выйти").last.click()
        page.wait_for_url(re.compile(r"/login"), timeout=8000)
        ctx.clear_cookies()

        login(page, "student2")
        check(page, "15-home-student2", width)
        page.goto(f"{BASE}/study")
        check(page, "16-radar-student2", width)
        page.get_by_role("link", name=re.compile("Теория автоматического управления")).first.click()
        check(page, "17-discipline-exam", width)
        fill = page.get_by_role("button", name="Заполнить максимумом")
        if fill.count():
            fill.click()
            page.get_by_role("button", name="Пересчитать").click()
            page.locator(".whatif-result").wait_for(timeout=8000)
            page.locator(".whatif-result").scroll_into_view_if_needed()
        check(page, "18-whatif", width)
        page.goto(f"{BASE}/study")
        page.get_by_role("link", name=re.compile("Теория механизмов и машин")).first.click()
        check(page, "19-discipline-critical", width)
        page.get_by_role("link", name=re.compile("Кинематический анализ")).first.click()
        check(page, "20-topic-materials", width)
        ctx.clear_cookies()

        login(page, "dekanat")
        check(page, "21-staff-queue", width)
        page.locator("a.list-row").first.click()
        check(page, "22-staff-application", width)
        page.goto(f"{BASE}/staff/grades")
        page.get_by_label("Факультет").select_option("РК")
        page.get_by_label("Кафедра").select_option("РК9")
        page.get_by_label("Группа").select_option("РК9-51Б")
        check(page, "23a-staff-group", width)
        page.locator("main a.list-row").first.click()
        page.wait_for_load_state("networkidle")
        check(page, "23-staff-grades", width)
        page.goto(f"{BASE}/staff/announcements")
        check(page, "24-staff-announcements", width, shot=width >= 500)
        browser.close()


for w, h in ((360, 780), (1280, 860)):
    run(w, h)
print("PROBLEMS:" if problems else "OK: no horizontal scroll, no console errors")
for x in problems:
    print(" -", x)
sys.exit(1 if problems else 0)
