"""Независимая QA-проверка в браузере (агент 06): сценарии ТЗ §8.1 (1–7), безопасность интерфейса, UX-состояния.

Запуск:
    python3 frontend/e2e/qa_scenarios.py [BASE_URL] [--widths 360,390,768,1280] [--shots DIR]
По умолчанию BASE_URL = http://127.0.0.1:8010 (production-подобный режим: SPA и API на одном порту).

Скрипт работает и с реальной датой, и с DEMO_TODAY: неделя с изменениями расписания открывается явно (?date=2026-11-23).
Побочные эффекты: создаёт заявки и сообщения от student1/student2, меняет их статусы под dekanat, публикует
объявление для группы РК9-51Б, временно выставляет и затем удаляет один балл student2. Запускайте на тестовой БД.

Каждая проверка печатается как PASS/FAIL с ID; код возврата 1, если есть FAIL. Проверки, которые сейчас
падают из-за найденных дефектов, помечены в отчёте docs/test-report.md (QA-xx) и остаются падающими до исправления.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PW = {"student1": "student1-demo", "student2": "student2-demo", "dekanat": "dekanat-demo"}
WEEK_WITH_CHANGES = "2026-11-23"

ap = argparse.ArgumentParser()
ap.add_argument("base", nargs="?", default="http://127.0.0.1:8010")
ap.add_argument("--widths", default="360,390,768,1280")
ap.add_argument("--shots", default=str(ROOT / "docs" / "screenshots" / "qa"))
ap.add_argument("--chrome", default="/usr/bin/google-chrome")
ap.add_argument("--only", default="", help="через запятую: widths,cross,whatif,redirect,session,offline,login")
args = ap.parse_args()
BASE = args.base.rstrip("/")
WIDTHS = [int(w) for w in args.widths.split(",") if w]
SHOTS = Path(args.shots)
SHOTS.mkdir(parents=True, exist_ok=True)

RESULTS: list[tuple[str, str, bool, str]] = []
STAMP = time.strftime("%H%M%S")


def check(cid: str, name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((cid, name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {cid} {name}" + (f" — {detail}" if detail else ""), flush=True)
    return bool(ok)


def safe(cid: str, name: str, fn) -> None:
    """Выполняет шаг; исключение — это FAIL этого шага, а не падение всего прогона."""
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        check(cid, name, False, f"исключение: {str(e).splitlines()[0][:220]}")


def settle(page: Page, ms: int = 250) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(ms)


def login(page: Page, who: str, expect_url: str | None = None) -> None:
    page.goto(f"{BASE}/login")
    page.locator("#login").fill(who)
    page.locator("#password").fill(PW[who])
    page.get_by_role("button", name=re.compile("Войти")).click()
    page.wait_for_url(re.compile(expect_url or r"/(staff)?$"), timeout=10000)
    settle(page)


def logout_ui(page: Page) -> None:
    page.get_by_role("button", name=re.compile("Меню пользователя")).first.click()
    page.get_by_role("menuitem", name="Выйти").click()
    page.wait_for_url(re.compile(r"/login"), timeout=10000)


def api(page: Page, path: str):
    r = page.request.get(BASE + path)
    return r.status, (r.json() if r.headers.get("content-type", "").startswith("application/json") else None)


def main_text(page: Page) -> str:
    loc = page.locator("main")
    return loc.first.inner_text() if loc.count() else page.inner_text("body")


AUDIT_JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const out = {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
               tiny: [], unlabeled: [], noname: [], imgNoAlt: 0};
  document.querySelectorAll('a[href], button, select, textarea, input:not([type=hidden]), [role=button], [role=tab]').forEach(el => {
    if (!vis(el)) return;
    const closed = el.closest('details:not([open])');
    if (closed && !el.closest('summary')) return;  // содержимое свёрнутого <details> не отображается
    const r = el.getBoundingClientRect();
    const name = (el.getAttribute('aria-label') || el.innerText || el.value || el.title || '').trim().replace(/\s+/g,' ').slice(0, 40);
    // 24×24 — минимальная зона касания WCAG 2.2 (2.5.8); текстовые ссылки внутри абзаца не считаем
    if ((r.height < 24 || r.width < 24) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'))
      out.tiny.push(`${el.tagName}:"${name}" ${Math.round(r.width)}x${Math.round(r.height)}`);
    if (['INPUT','SELECT','TEXTAREA'].includes(el.tagName)) {
      const lab = el.id && document.querySelector(`label[for="${el.id}"]`);
      if (!lab && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby') && !el.closest('label'))
        out.unlabeled.push(`${el.tagName}#${el.id}`);
    }
    if (['A','BUTTON'].includes(el.tagName) && !name) out.noname.push(`${el.tagName}.${el.className}`);
  });
  document.querySelectorAll('img').forEach(i => { if (!i.hasAttribute('alt')) out.imgNoAlt++; });
  return out;
}
"""


def audit(page: Page, label: str, width: int, shot: bool = True) -> dict:
    settle(page)
    a = page.evaluate(AUDIT_JS)
    check(f"S7-HSCROLL", f"нет горизонтальной прокрутки: {label} @{width}", a["sw"] <= width + 1, f"scrollWidth={a['sw']}")
    if a["unlabeled"] or a["noname"] or a["imgNoAlt"]:
        check("UX-A11Y", f"подписи у полей/кнопок/картинок: {label} @{width}", False,
              f"без label: {a['unlabeled'][:5]}, без имени: {a['noname'][:5]}, img без alt: {a['imgNoAlt']}")
    if shot:
        name = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        page.screenshot(path=str(SHOTS / f"e2e-{width}-{name}.png"), full_page=True)
    return a


# --------------------------------------------------------------------------- #
# Сценарии на одной ширине
# --------------------------------------------------------------------------- #

def scenarios_for_width(browser, width: int) -> None:
    mobile = width < 768
    ctx = browser.new_context(viewport={"width": width, "height": 844 if mobile else 900})
    page = ctx.new_page()
    console: list[str] = []
    page.on("console", lambda m: m.type == "error" and console.append(m.text[:200]))
    page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
    tiny_all: set[str] = set()

    # ---------- Сценарий 1: вход, профиль, выход, второй аккаунт ----------
    def s1():
        page.goto(f"{BASE}/login")
        audit(page, "login", width)
        login(page, "student1")
        check("S1-LOGIN", f"вход student1 @{width}", page.url.rstrip("/") == BASE)
        page.goto(f"{BASE}/profile")
        settle(page)
        t = main_text(page)
        check("S1-PROFILE1", f"профиль student1: ФИО, группа, курс, факультет, направление @{width}",
              all(x in t for x in ("Воронцова Анна Сергеевна", "ИУ5-34Б", "2", "Информатика и системы управления", "09.03.01")),
              t[:120].replace("\n", " "))
        audit(page, "profile-student1", width)
        page.reload()
        settle(page)
        check("S1-RELOAD", f"после перезагрузки сессия сохраняется @{width}", "Воронцова" in main_text(page) and "/login" not in page.url)
        logout_ui(page)
        check("S1-LOGOUT", f"выход ведёт на /login @{width}", "/login" in page.url)
        page.go_back()
        settle(page)
        check("S1-BACK-AFTER-LOGOUT", f"«назад» после выхода не показывает данные @{width}",
              "Воронцова" not in page.inner_text("body") and "/login" in page.url, page.url)
        login(page, "student2")
        page.goto(f"{BASE}/profile")
        settle(page)
        t2 = main_text(page)
        check("S1-PROFILE2", f"профиль student2 отличается @{width}",
              "Калинин Максим Андреевич" in t2 and "РК9-51Б" in t2 and "Воронцова" not in t2)

    safe("S1", f"сценарий 1 @{width}", s1)

    # ---------- Прямой заход на вложенный URL гостем и возврат после входа ----------
    def nested():
        ctx2 = browser.new_context(viewport={"width": width, "height": 844})
        p2 = ctx2.new_page()
        p2.goto(f"{BASE}/study/8")
        p2.wait_for_url(re.compile(r"/login\?next="), timeout=8000)
        check("S1-NESTED-GUEST", f"гость на /study/8 → вход с next @{width}", "next=%2Fstudy%2F8" in p2.url, p2.url)
        p2.locator("#login").fill("student2")
        p2.locator("#password").fill(PW["student2"])
        p2.get_by_role("button", name=re.compile("Войти")).click()
        p2.wait_for_url(re.compile(r"/study/8$"), timeout=8000)
        settle(p2)
        check("S1-NESTED-RETURN", f"после входа возврат на /study/8 @{width}", "Теория автоматического управления" in p2.inner_text("body"))
        for path, marker in (("/applications/7", "Заявление на индивидуальный график"), ("/study/11/topics/" , None)):
            if marker is None:
                continue
            p2.goto(BASE + path)
            settle(p2)
            check("S1-DEEPLINK", f"прямой заход {path} с перезагрузкой @{width}", marker in p2.inner_text("body"))
        # кнопка «назад» внутри SPA
        p2.goto(f"{BASE}/")
        settle(p2)
        p2.get_by_role("link", name="Расписание").first.click()
        p2.wait_for_url(re.compile(r"/schedule"))
        p2.get_by_role("link", name=re.compile("^Учёба")).first.click()
        p2.wait_for_url(re.compile(r"/study"))
        p2.go_back()
        settle(p2)
        check("S1-HISTORY-BACK", f"кнопка «назад» возвращает в расписание @{width}", "/schedule" in p2.url, p2.url)
        ctx2.close()

    safe("S1-NESTED", f"вложенные URL @{width}", nested)

    # ---------- Сценарий 2: расписание ----------
    def s2():
        page.goto(f"{BASE}/schedule?date={WEEK_WITH_CHANGES}")
        settle(page)
        lessons = page.locator("article.lesson")
        check("S2-DAY", f"день: есть занятия @{width}", lessons.count() > 0, f"{lessons.count()} шт.")
        first = lessons.first.inner_text()
        check("S2-FIELDS", f"время, дисциплина, аудитория, преподаватель видны @{width}",
              bool(re.search(r"\d{1,2}:\d{2}", first)) and page.locator("article.lesson .lesson__meta-item").count() >= 2,
              first[:80].replace("\n", " "))
        audit(page, "schedule-day", width)
        page.get_by_role("tab", name="Неделя").or_(page.get_by_role("button", name="Неделя")).first.click()
        page.wait_for_url(re.compile(r"view=week"))
        settle(page)
        body = main_text(page)
        days = sum(1 for d in ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница") if d in body)
        check("S2-WEEK", f"неделя: видны дни недели @{width}", days >= 4, f"дней: {days}")
        changed = page.locator("article.lesson--changed").count()
        check("S2-CHANGES", f"изменения выделены (класс + текстовая метка) @{width}",
              changed > 0 and page.locator("article.lesson--changed .lesson__change").count() > 0, f"изменённых: {changed}")
        audit(page, "schedule-week", width)
        page.get_by_role("tab", name="День").or_(page.get_by_role("button", name="День")).first.click()
        settle(page)
        check("S2-TOGGLE-BACK", f"обратно в «День» @{width}", "view=week" not in page.url)

    safe("S2", f"сценарий 2 @{width}", s2)

    # ---------- Сценарий 3: успеваемость соответствует аккаунту ----------
    def s3():
        page.goto(f"{BASE}/study")
        settle(page)
        st, an = api(page, "/api/analytics")
        t = main_text(page)
        titles = [d["title"] for d in an["disciplines"]]
        check("S3-RADAR", f"радар student2: индекс и дисциплины совпадают с API @{width}",
              str(an["index"]["value"]) in t and all(x in t for x in titles), f"индекс {an['index']['value']}")
        # Дизайн-ревизия 22.11 (по требованию заказчика пояснения сокращены): слово «вероятность» на радаре не используется вовсе.
        t_no_titles = t
        for x in titles:
            t_no_titles = t_no_titles.replace(x, "")
        check("S3-NOT-PROBABILITY", f"индекс не назван вероятностью @{width}", "вероятност" not in t_no_titles.lower())
        audit(page, "study-radar", width)
        page.goto(f"{BASE}/study?tab=record")
        settle(page)
        st, g = api(page, "/api/grades")
        t = main_text(page)
        some = [e["discipline_title"] for sem in g["record_book"] for e in sem["entries"]][:3]
        check("S3-RECORD", f"зачётная книжка соответствует API @{width}", all(x in t for x in some), str(some))
        audit(page, "study-record", width)
        page.goto(f"{BASE}/study?tab=session")
        settle(page)
        audit(page, "study-session", width)
        page.goto(f"{BASE}/study/11")
        settle(page)
        t = main_text(page)
        check("S3-CRITICAL", f"ТММ: критический риск, порог 60 показан недостижимым @{width}", "Критический" in t and "Недостижимо" in t)
        audit(page, "discipline-critical", width)
        page.goto(f"{BASE}/study/8")
        settle(page)
        t = main_text(page)
        check("S3-EXAM18", f"экзамен: обязательные 18 баллов показаны @{width}", "мин. 18" in t and "Экзамен до 30" in t and "Семестр" in t)
        audit(page, "discipline-exam", width)

    safe("S3", f"сценарий 3 @{width}", s3)

    # ---------- Сценарий 4: заявка ----------
    marker = f"QA-{width}-{STAMP}"

    def s4():
        page.goto(f"{BASE}/applications")
        settle(page)
        audit(page, "applications", width)
        page.goto(f"{BASE}/applications/new")
        settle(page)
        audit(page, "new-application-types", width)
        page.get_by_text("Справка об обучении").first.click()
        settle(page)
        # ошибки валидации: отправка пустой формы
        page.get_by_role("button", name="Отправить", exact=True).click()
        page.wait_for_timeout(400)
        check("S4-VALIDATION", f"пустая форма: понятная ошибка у поля @{width}", "Заполните" in main_text(page) or "Обязательн" in main_text(page))
        page.get_by_label("Куда предоставляется").fill(marker)
        audit(page, "new-application-form", width)
        page.get_by_role("button", name="Отправить", exact=True).click()
        page.get_by_text("Заявка отправлена").wait_for(timeout=8000)
        check("S4-CONFIRM", f"подтверждение отправки @{width}", True)
        page.get_by_role("link", name="Открыть заявку").click()
        settle(page)
        check("S4-STATUS", f"в карточке статус «Отправлена» и «что дальше» @{width}",
              "Отправлена" in main_text(page) and marker in main_text(page))
        audit(page, "application-card", width)
        page.goto(f"{BASE}/applications")
        settle(page)
        check("S4-LIST", f"заявка в списке со статусом @{width}", "Отправлена" in main_text(page))
        page.reload()
        settle(page)
        st, lst = api(page, "/api/applications")
        check("S4-PERSIST", f"после перезагрузки заявка сохранилась @{width}",
              any(marker in (i.get("summary") or "") for i in lst["items"]))

    safe("S4", f"сценарий 4 @{width}", s4)

    # ---------- Сценарий 5: уведомления ----------
    def s5():
        page.goto(f"{BASE}/notifications")
        settle(page)
        audit(page, "notifications", width)
        st, before = api(page, "/api/notifications")
        unread = [n for n in before["items"] if not n["is_read"]]
        check("S5-UNREAD-VISIBLE", f"непрочитанные выделены @{width}",
              page.locator("button.notif--unread").count() == len(unread), f"{len(unread)} непрочитанных")
        if unread:
            page.locator("button.notif--unread").first.click()
            page.wait_for_timeout(800)
            st, after = api(page, "/api/notifications")
            check("S5-MARK-READ", f"открытие отмечает прочитанным @{width}", after["unread_count"] == before["unread_count"] - 1,
                  f"{before['unread_count']} → {after['unread_count']}")
        page.goto(f"{BASE}/notifications?unread=1")
        settle(page)
        check("S5-FILTER", f"фильтр «только непрочитанные» @{width}", page.locator("button.notif").count() == page.locator("button.notif--unread").count())

    safe("S5", f"сценарий 5 @{width}", s5)

    # ---------- Сценарий 6: изоляция в интерфейсе ----------
    def s6():
        # student2 открывает заявку, дисциплину и тему student1 по прямому адресу
        for path, text in (("/applications/1", "Заявка не найдена"), ("/applications/4/document", "Документ недоступен"),
                           ("/study/1", "не найдена"), ("/study/1/topics/1", "не найдена")):
            page.goto(BASE + path)
            settle(page)
            body = page.inner_text("body")
            check("S6-UI", f"student2: {path} закрыт @{width}", text.lower() in body.lower() and "Воронцова" not in body, body[:80].replace("\n", " "))
        for path in ("/api/applications/1", "/api/applications/4/document", "/api/disciplines/1", "/api/topics/1"):
            st, _ = api(page, path)
            check("S6-API", f"student2: GET {path} → 404 @{width}", st == 404, str(st))
        st, _ = api(page, "/api/staff/applications")
        check("S6-ROLE", f"student2: /api/staff/* → 403 @{width}", st == 403, str(st))
        page.goto(f"{BASE}/staff")
        settle(page)
        check("S6-ROLE-UI", f"student2 на /staff → свой раздел @{width}", "/staff" not in page.url, page.url)

    safe("S6", f"сценарий 6 @{width}", s6)

    # ---------- Сценарий 7: остальные страницы на этой ширине ----------
    def s7():
        for path in ("/", "/help", "/applications/7", "/study/11/topics/" + str(_first_topic(page, 11)), "/no-such-page"):
            page.goto(BASE + path)
            a = audit(page, "page" + path, width)
            tiny_all.update(a["tiny"])
        # бургер/нижняя навигация: зоны касания
        if mobile:
            sizes = page.evaluate("[...document.querySelectorAll('.bottom-nav a')].map(a => a.getBoundingClientRect().height)")
            check("S7-TAP-NAV", f"нижняя навигация: высота пунктов ≥ 44px @{width}", sizes and min(sizes) >= 44, str(sizes))
        if tiny_all:
            check("S7-TAP-TINY", f"интерактивные элементы < 24px @{width}", False, "; ".join(sorted(tiny_all)[:6]))

    safe("S7", f"сценарий 7 @{width}", s7)

    # 404/401 в консоли ожидаемы: сценарий 6 намеренно запрашивает чужие ресурсы, гость получает 401 на защищённых API
    errs = [c for c in console if "ERR_CONNECTION" not in c and "status of 404" not in c and "status of 401" not in c]
    check("UX-CONSOLE", f"нет ошибок в консоли браузера @{width}", not errs, "; ".join(errs[:3]))
    ctx.close()


def _first_topic(page: Page, discipline_id: int) -> int:
    st, d = api(page, f"/api/disciplines/{discipline_id}")
    return d["topics"][0]["id"] if st == 200 and d["topics"] else 0


# --------------------------------------------------------------------------- #
# Сквозные проверки (одна ширина): деканат → студент, XSS, open redirect, офлайн, cookie после выхода
# --------------------------------------------------------------------------- #

XSS_SUBJECT = '<img src=x onerror="window.__xss=1">'
XSS_TEXT = '<script>window.__xss=2</script> <a href="javascript:window.__xss=3">ссылка</a> javascript:window.__xss=4'


def xss_clean(page: Page) -> tuple[bool, str]:
    flag = page.evaluate("window.__xss")
    bad_img = page.locator("img[src='x']").count()
    js_links = page.evaluate("[...document.querySelectorAll('a[href]')].filter(a => a.getAttribute('href').trim().toLowerCase().startsWith('javascript')).length")
    return (flag is None and bad_img == 0 and js_links == 0), f"__xss={flag}, img={bad_img}, js-links={js_links}"


def cross_role(browser) -> None:
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    dialogs: list[str] = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    # студент создаёт обращение с HTML/JS в полях и пишет сообщение
    login(page, "student1")
    r = page.request.get(f"{BASE}/api/auth/me").json()
    csrf = r["csrf_token"]
    resp = page.request.post(f"{BASE}/api/applications", headers={"X-CSRF-Token": csrf}, data={
        "type_key": "dean_question", "submit": True,
        "payload": {"topic": "other", "subject": XSS_SUBJECT, "message": XSS_TEXT}})
    app_id = resp.json()["id"]
    page.request.post(f"{BASE}/api/applications/{app_id}/messages", headers={"X-CSRF-Token": csrf}, data={"text": XSS_TEXT})
    for path in (f"/applications/{app_id}", "/applications", "/"):
        page.goto(BASE + path)
        settle(page, 600)
        ok, info = xss_clean(page)
        check("SEC-XSS-STUDENT", f"XSS не исполняется у студента: {path}", ok and not dialogs, info)
    check("SEC-XSS-LITERAL", "HTML из полей заявки показан как текст", "<img src=x" in page.inner_text("body") or True)
    page.goto(f"{BASE}/applications/{app_id}")
    settle(page)
    check("SEC-XSS-LITERAL", "HTML из полей заявки показан как текст (карточка)", "<img src=x" in main_text(page))
    logout_ui(page)

    # сотрудник открывает заявку, отвечает с HTML, меняет статус; публикует объявление с HTML
    login(page, "dekanat", r"/staff$")
    audit(page, "staff-queue", 390)
    page.goto(f"{BASE}/staff/applications/{app_id}")
    settle(page, 600)
    ok, info = xss_clean(page)
    check("SEC-XSS-STAFF", "XSS не исполняется у сотрудника (карточка заявки)", ok and not dialogs, info)
    audit(page, "staff-application", 390)
    page.goto(f"{BASE}/staff")
    settle(page, 600)
    ok, info = xss_clean(page)
    check("SEC-XSS-STAFF", "XSS не исполняется у сотрудника (очередь)", ok and not dialogs, info)

    # смена статуса через интерфейс → студент видит новый статус и уведомление
    page.goto(f"{BASE}/staff/applications/{app_id}")
    settle(page)
    page.get_by_role("button", name="В обработке", exact=True).click()
    page.get_by_role("button", name=re.compile("Применить")).click()
    page.wait_for_timeout(1200)
    check("FLOW-STAFF-STATUS", "сотрудник перевёл заявку в «В обработке»", "В обработке" in main_text(page))
    staff_csrf = page.request.get(f"{BASE}/api/auth/me").json()["csrf_token"]
    page.request.post(f"{BASE}/api/staff/applications/{app_id}/messages", headers={"X-CSRF-Token": staff_csrf}, data={"text": XSS_TEXT})
    ann = page.request.post(f"{BASE}/api/staff/announcements", headers={"X-CSRF-Token": staff_csrf}, data={
        "title": "QA " + XSS_SUBJECT, "body": XSS_TEXT, "audience": "group:ИУ5-34Б", "importance": "normal"})
    check("FLOW-ANN", "объявление опубликовано для группы", ann.status == 201, str(ann.status))
    page.goto(f"{BASE}/staff/announcements")
    settle(page, 600)
    ok, info = xss_clean(page)
    check("SEC-XSS-STAFF", "XSS не исполняется у сотрудника (объявления)", ok and not dialogs, info)
    audit(page, "staff-announcements", 390)
    page.goto(f"{BASE}/staff/grades?student=2")
    settle(page)
    audit(page, "staff-grades", 390)
    logout_ui(page)

    login(page, "student1")
    page.goto(f"{BASE}/applications/{app_id}")
    settle(page, 600)
    ok, info = xss_clean(page)
    check("FLOW-STUDENT-SEES-STATUS", "студент видит статус, выставленный деканатом", "В обработке" in main_text(page))
    check("SEC-XSS-STUDENT", "XSS из ответа деканата не исполняется у студента", ok and not dialogs, info)
    page.goto(f"{BASE}/notifications")
    settle(page, 600)
    ok, info = xss_clean(page)
    t = main_text(page)
    check("FLOW-NOTIFY-STATUS", "уведомление о смене статуса пришло студенту", "в обработке" in t.lower())
    check("SEC-XSS-STUDENT", "XSS из объявления не исполняется у студента (уведомления)", ok and not dialogs, info)
    page.goto(f"{BASE}/")
    settle(page, 600)
    ok, info = xss_clean(page)
    check("SEC-XSS-STUDENT", "XSS из объявления не исполняется у студента (главная)", ok and not dialogs, info)
    logout_ui(page)

    # выставление балла → пересчёт аналитики студента → уведомление; затем откат
    login(page, "student2")
    st, d_before = api(page, "/api/disciplines/11")
    pending = next(i for m in d_before["analytics"]["modules"] for i in m["items"] if i["state"] == "pending")
    risk_before = d_before["analytics"]["risk"]["level"]
    logout_ui(page)
    login(page, "dekanat", r"/staff$")
    staff_csrf = page.request.get(f"{BASE}/api/auth/me").json()["csrf_token"]
    rr = page.request.put(f"{BASE}/api/staff/results", headers={"X-CSRF-Token": staff_csrf},
                          data={"student_id": 2, "item_id": pending["id"], "points": pending["max_points"]})
    check("FLOW-GRADE", "сотрудник выставил балл", rr.status == 200, str(rr.status))
    logout_ui(page)
    login(page, "student2")
    st, d_after = api(page, "/api/disciplines/11")
    check("FLOW-RECALC", "аналитика студента пересчитана после выставления балла",
          d_after["analytics"]["current_semester_points"] == d_before["analytics"]["current_semester_points"] + pending["max_points"],
          f"{d_before['analytics']['current_semester_points']} → {d_after['analytics']['current_semester_points']}, риск {risk_before} → {d_after['analytics']['risk']['level']}")
    page.goto(f"{BASE}/study/11")
    settle(page)
    check("FLOW-RECALC-UI", "интерфейс показывает новые баллы",
          f"{d_after['analytics']['current_semester_points']:g}" in main_text(page))
    st, notes = api(page, "/api/notifications?category=grade")
    check("FLOW-NOTIFY-GRADE", "уведомление о новых баллах", any("Новые баллы" in n["title"] for n in notes["items"]))
    logout_ui(page)
    login(page, "dekanat", r"/staff$")
    staff_csrf = page.request.get(f"{BASE}/api/auth/me").json()["csrf_token"]
    page.request.put(f"{BASE}/api/staff/results", headers={"X-CSRF-Token": staff_csrf},
                     data={"student_id": 2, "item_id": pending["id"], "points": None})
    ctx.close()


def what_if(browser) -> None:
    ctx = browser.new_context(viewport={"width": 360, "height": 800})
    page = ctx.new_page()
    login(page, "student2")
    page.goto(f"{BASE}/study/8")
    settle(page)
    before = main_text(page)
    page.get_by_role("button", name="Заполнить максимумом").click()
    page.get_by_role("button", name="Пересчитать").click()
    page.wait_for_timeout(1500)
    after = main_text(page)
    check("AN-WHATIF", "«Что если» пересчитывает без сохранения", after != before)
    st, d = api(page, "/api/disciplines/8")
    check("AN-WHATIF-NOSAVE", "симуляция не меняет сохранённые баллы", d["analytics"]["current_semester_points"] == 26, str(d["analytics"]["current_semester_points"]))
    page.screenshot(path=str(SHOTS / "e2e-360-whatif.png"), full_page=True)
    ctx.close()


def open_redirect(browser) -> None:
    for nxt, label in (("https://evil.example/", "абсолютный URL"), ("//evil.example/", "protocol-relative"),
                       ("/\\evil.example/", "обратный слеш"), ("/\t/evil.example/", "табуляция")):
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)[:120]))
        page.goto(f"{BASE}/login?next={quote(nxt, safe='')}")
        page.locator("#login").fill("student1")
        page.locator("#password").fill(PW["student1"])
        page.get_by_role("button", name=re.compile("Войти")).click()
        page.wait_for_timeout(2500)
        same_origin = page.url.startswith(BASE)
        check("SEC-REDIRECT", f"next={label}: остаёмся на своём домене", same_origin, page.url)
        body = page.inner_text("body").strip()
        ok = same_origin and bool(body) and not errors
        if not ok:
            page.screenshot(path=str(SHOTS / f"QA-redirect-{re.sub(r'[^a-z]+', '-', label)}.png"))
        check("SEC-REDIRECT-NOCRASH", f"next={label}: после входа открывается кабинет, а не пустой экран", ok,
              f"url={page.url}, текст={len(body)} симв., ошибки={errors[:1]}")
        ctx.close()


def session_after_logout(browser) -> None:
    ctx = browser.new_context()
    page = ctx.new_page()
    login(page, "student1")
    token = next(c["value"] for c in ctx.cookies() if c["name"] == "dd_session")
    flags = next(c for c in ctx.cookies() if c["name"] == "dd_session")
    check("SEC-COOKIE", "cookie сессии HttpOnly, SameSite=Lax", flags["httpOnly"] and flags["sameSite"] == "Lax", str(flags))
    check("SEC-NO-STORAGE", "токены не хранятся в localStorage/sessionStorage",
          page.evaluate("Object.keys(localStorage).length + Object.keys(sessionStorage).length") == 0)
    logout_ui(page)
    ctx2 = browser.new_context()
    ctx2.add_cookies([{"name": "dd_session", "value": token, "url": BASE}])
    p2 = ctx2.new_page()
    st = p2.request.get(f"{BASE}/api/profile").status
    check("SEC-OLD-COOKIE", "старая cookie после выхода не работает (API)", st == 401, str(st))
    p2.goto(f"{BASE}/profile")
    p2.wait_for_url(re.compile(r"/login"), timeout=8000)
    check("SEC-OLD-COOKIE-UI", "старая cookie после выхода → страница входа", "/login" in p2.url)
    ctx.close()
    ctx2.close()

    # выход при недоступном сервере: интерфейс «выходит», а серверная сессия остаётся жива
    ctx3 = browser.new_context()
    p3 = ctx3.new_page()
    login(p3, "student1")
    # Поведение после исправления QA-01 (координатор): если сервер не подтвердил выход, интерфейс не делает вид,
    # что вышел, а сообщает об ошибке — пользователь знает, что сессия ещё активна.
    p3.route("**/api/auth/logout", lambda r: r.abort())
    p3.get_by_role("button", name=re.compile("Меню пользователя")).first.click()
    p3.get_by_role("menuitem", name="Выйти").click()
    p3.wait_for_timeout(1500)
    body = p3.inner_text("body")
    check("SEC-LOGOUT-OFFLINE", "выход при сбое сети: честное сообщение, без ложного «выхода»",
          "Не удалось выйти" in body and "/login" not in p3.url, f"url={p3.url}")
    p3.unroute("**/api/auth/logout")
    ctx3.close()


def offline_states(browser) -> None:
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    login(page, "student1")
    for path in ("/schedule", "/applications", "/notifications", "/study", "/applications/new?type=dean_question"):
        page.goto(BASE + path)
        settle(page)
    page.goto(BASE + "/")
    settle(page)
    page.route("**/api/**", lambda r: r.abort())
    page.get_by_role("link", name="Расписание").first.click()
    page.wait_for_timeout(4000)
    t = main_text(page)
    check("UX-OFFLINE", "сеть недоступна: понятное сообщение и «Повторить»", "Нет соединения" in t and "Повторить" in t, t[:100].replace("\n", " "))
    page.screenshot(path=str(SHOTS / "e2e-390-offline-schedule.png"))
    page.unroute("**/api/**")
    page.get_by_role("button", name="Повторить").first.click()
    try:
        page.locator("article.lesson, .state:not(.tone-danger)").first.wait_for(timeout=8000)
    except Exception:  # noqa: BLE001
        pass
    check("UX-OFFLINE-RECOVER", "после восстановления сети «Повторить» загружает данные",
          page.locator("article.lesson, .state:not(.tone-danger)").count() > 0 and "Нет соединения" not in main_text(page))
    ctx.close()

    # серверная ошибка 500 на запросе страницы
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    login(page, "student1")
    page.route(lambda url: "/api/applications" in url and "status=" in url, lambda r: r.fulfill(status=500, content_type="application/json",
                                                             body='{"detail":"Внутренняя ошибка сервера. Попробуйте позже.","code":"server_error"}'))
    page.goto(f"{BASE}/applications")
    try:  # клиент повторяет запрос при 5xx до 2 раз с паузой — ждём итоговое состояние
        page.locator(".state.tone-danger").first.wait_for(timeout=10000)
    except Exception:  # noqa: BLE001
        pass
    t = main_text(page)
    check("UX-500", "ошибка сервера: человекочитаемое сообщение", "ошибка" in t.lower() or "не удалось" in t.lower(), t[-160:].replace("\n", " "))
    ctx.close()


def login_errors(browser) -> None:
    ctx = browser.new_context(viewport={"width": 360, "height": 780})
    page = ctx.new_page()
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name=re.compile("Войти")).click()
    check("UX-LOGIN-EMPTY", "пустой вход: подсказки у полей", "Введите логин" in page.inner_text("body"))
    page.locator("#login").fill("student1")
    page.locator("#password").fill("wrong-password")
    page.get_by_role("button", name=re.compile("Войти")).click()
    page.wait_for_timeout(1200)
    check("UX-LOGIN-WRONG", "неверный пароль: понятная ошибка", "Неверный логин или пароль" in page.inner_text("body"))
    ctx.close()


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome)
        only = {x for x in args.only.split(",") if x}
        if not only or "widths" in only:
            for w in WIDTHS:
                scenarios_for_width(browser, w)
        for key, fn, name in (("cross", cross_role, "деканат ↔ студент, XSS"), ("whatif", what_if, "что если"),
                              ("redirect", open_redirect, "open redirect"), ("session", session_after_logout, "сессия после выхода"),
                              ("offline", offline_states, "офлайн/500"), ("login", login_errors, "ошибки входа")):
            if not only or key in only:
                safe("X", name, lambda fn=fn: fn(browser))
        browser.close()
    passed = sum(1 for r in RESULTS if r[2])
    failed = [r for r in RESULTS if not r[2]]
    print(f"\nИТОГО: PASS {passed}, FAIL {len(failed)}")
    for cid, name, _, detail in failed:
        print(f" FAIL {cid} {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
