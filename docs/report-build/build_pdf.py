"""Сборка PDF-версии отчёта об ИИ-разработке.

docs/ai_development_report.md → docs/report-build/report.html → docs/ai_development_report.pdf

Markdown превращается в HTML (python-markdown), к нему добавляются стили для печати (шрифт Manrope с кириллицей,
self-hosted из ./fonts), полноразмерные скриншоты заменяются фрагментами из ./img (см. FIGURES), относительные ссылки
на файлы репозитория выводятся как текст (в PDF они бы не открылись). Печать — Chrome через Playwright (page.pdf()).

Запуск из корня репозитория:  python3 docs/report-build/build_pdf.py
Зависимости: markdown, playwright (Python), Google Chrome (/usr/bin/google-chrome или путь в CHROME).
Фрагменты скриншотов (./img) получены обрезкой файлов docs/screenshots/ (см. CROPS) — пересоздать: --crops (нужен Pillow).
"""
from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
MD = DOCS / "ai_development_report.md"
HTML_OUT = HERE / "report.html"
PDF_OUT = DOCS / "ai_development_report.pdf"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")

# Скриншот в markdown → фрагменты для PDF (полноразмерные страницы слишком высокие для A4).
FIGURES: dict[str, list[str]] = {
    "screenshots/01-login-desktop.png": ["img/login.png"],
    "screenshots/02-home-student1-mobile.png": ["img/home-s1-mobile.png"],
    "screenshots/15-home-student2-mobile.png": ["img/home-s2-mobile.png"],
    "screenshots/04-schedule-week-desktop.png": ["img/schedule-week.png"],
    "screenshots/16-radar-student2-desktop.png": ["img/radar-s2.png"],
    "screenshots/18-whatif-desktop.png": ["img/discipline-exam.png", "img/whatif-result.png"],
    "screenshots/20-topic-materials-desktop.png": ["img/topic-materials.png"],
    "screenshots/10-application-card-desktop.png": ["img/application-card.png"],
    "screenshots/22-staff-application-desktop.png": ["img/staff-application.png"],
    "report-build/img/quick-actions-before.png": ["img/quick-actions-before.png"],
    "report-build/img/quick-actions-after.png": ["img/quick-actions-after.png"],
}

# Как получены фрагменты: (исходный скриншот, (left, top, right, bottom)) — левая панель навигации отрезана.
CROPS: dict[str, tuple[str, tuple[int, int, int, int]]] = {
    "login.png": ("01-login-desktop.png", (0, 0, 1280, 860)),
    "home-s1-mobile.png": ("02-home-student1-mobile.png", (0, 0, 720, 1560)),
    "home-s2-mobile.png": ("15-home-student2-mobile.png", (0, 0, 720, 1560)),
    "schedule-week.png": ("04-schedule-week-desktop.png", (262, 90, 1280, 1640)),
    "radar-s2.png": ("16-radar-student2-desktop.png", (262, 90, 1280, 1330)),
    "discipline-exam.png": ("18-whatif-desktop.png", (262, 90, 1280, 1640)),
    "whatif-result.png": ("18-whatif-desktop.png", (262, 2120, 1280, 2840)),
    "topic-materials.png": ("20-topic-materials-desktop.png", (262, 90, 1280, 1260)),
    "application-card.png": ("10-application-card-desktop.png", (262, 90, 1280, 1010)),
    "staff-application.png": ("22-staff-application-desktop.png", (262, 90, 1280, 1000)),
    "quick-actions-before.png": ("02-home-student1-desktop.png", (928, 222, 1252, 376)),
    # quick-actions-after.png — снимок текущей сборки (агент 07, Playwright, 1280 px), не обрезка
}

# Перед этими разделами — новая страница
PAGE_BREAK_BEFORE = ("Как устроен документ", "11.1 Подход", "11.2 Промпты", "11.3 Процесс", "Скриншоты")

CSS = r"""
@font-face { font-family: 'Manrope'; font-weight: 400; src: url('fonts/manrope-cyrillic-400-normal.woff2') format('woff2'); unicode-range: U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116; }
@font-face { font-family: 'Manrope'; font-weight: 400; src: url('fonts/manrope-latin-400-normal.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: 'Manrope'; font-weight: 600; src: url('fonts/manrope-cyrillic-600-normal.woff2') format('woff2'); unicode-range: U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116; }
@font-face { font-family: 'Manrope'; font-weight: 600; src: url('fonts/manrope-latin-600-normal.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: 'Manrope'; font-weight: 700; src: url('fonts/manrope-cyrillic-700-normal.woff2') format('woff2'); unicode-range: U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116; }
@font-face { font-family: 'Manrope'; font-weight: 700; src: url('fonts/manrope-latin-700-normal.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: 'Manrope'; font-weight: 800; src: url('fonts/manrope-cyrillic-800-normal.woff2') format('woff2'); unicode-range: U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116; }
@font-face { font-family: 'Manrope'; font-weight: 800; src: url('fonts/manrope-latin-800-normal.woff2') format('woff2'); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }

@page { size: A4; margin: 15mm 15mm 17mm 15mm; }
:root { --ink: #151a2d; --muted: #5a6275; --line: #dfe3ec; --soft: #f3f4fa; --accent: #3b44d1; --accent-soft: #eceefe; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Manrope', 'DejaVu Sans', sans-serif; color: var(--ink); font-size: 9.6pt; line-height: 1.5; margin: 0; }
h1, h2, h3, h4 { line-height: 1.22; break-after: avoid; page-break-after: avoid; }
h1 { font-size: 23pt; font-weight: 800; letter-spacing: -0.02em; margin: 0 0 4mm; }
h2 { font-size: 15pt; font-weight: 800; margin: 7mm 0 2.5mm; padding-bottom: 1.5mm; border-bottom: 2px solid var(--accent); }
h3 { font-size: 11.2pt; font-weight: 700; margin: 5mm 0 2mm; color: #23295e; }
h2.break { break-before: page; page-break-before: always; margin-top: 0; }
p { margin: 0 0 2.4mm; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 2.6mm; padding-left: 5.5mm; }
li { margin: 0.6mm 0; }
li > ul, li > ol { margin: 0.6mm 0; }
strong { font-weight: 700; }
hr { display: none; }
code { font-family: 'DejaVu Sans Mono', monospace; font-size: 0.84em; background: var(--soft); border-radius: 3px; padding: 0.2mm 0.8mm; overflow-wrap: break-word; }
pre { font-family: 'DejaVu Sans Mono', monospace; font-size: 7.3pt; line-height: 1.38; background: var(--soft); border: 1px solid var(--line); border-radius: 2mm; padding: 3mm 3.5mm; white-space: pre; overflow: hidden; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
blockquote { margin: 2mm 0 3mm; padding: 2mm 4mm; border-left: 3px solid var(--accent); background: var(--accent-soft); border-radius: 0 2mm 2mm 0; color: #262c55; }
blockquote p { margin: 0.6mm 0; }
table { width: 100%; border-collapse: collapse; margin: 1.5mm 0 3.5mm; font-size: 8.1pt; line-height: 1.38; }
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th { text-align: left; font-weight: 700; background: #e9ebf6; color: #1e2350; }
th, td { border: 1px solid var(--line); padding: 1.3mm 1.8mm; vertical-align: top; overflow-wrap: break-word; word-break: normal; hyphens: manual; }
td code, th code { overflow-wrap: anywhere; }
td:first-child { min-width: 9mm; }
tbody tr:nth-child(even) td { background: #fafbfe; }
.ref { color: #2b33a8; font-weight: 600; }
.ref code { color: #2b33a8; background: var(--accent-soft); }
/* Обложка */
.cover-kicker { display: inline-block; font-size: 8.5pt; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent); background: var(--accent-soft); border-radius: 99px; padding: 1mm 3mm; margin-bottom: 4mm; }
.cover-meta { display: grid; grid-template-columns: 34mm 1fr; gap: 1mm 4mm; font-size: 8.6pt; color: var(--muted); margin: 0 0 4mm; }
.cover-meta b { color: var(--ink); font-weight: 600; }
.summary { background: linear-gradient(180deg, #f6f7ff, #eef0fd); border: 1px solid #d6daf8; border-radius: 3mm; padding: 1mm 5mm 2mm; margin-top: 4mm; }
.summary h2 { border: none; margin-top: 3mm; font-size: 13pt; }
/* Рисунки */
figure { margin: 3mm 0 5mm; break-inside: auto; }
figure .shots { display: flex; gap: 5mm; justify-content: center; align-items: flex-start; }
figure img { display: block; max-width: 100%; max-height: 232mm; width: auto; height: auto; margin: 0 auto 2.5mm; border: 1px solid var(--line); border-radius: 2mm; break-inside: avoid; }
figure.keep { break-inside: avoid; page-break-inside: avoid; }
figure .shots img { max-width: 48%; margin: 0; }
figure .shots.small img { max-width: 70mm; }
figcaption { font-size: 8.4pt; line-height: 1.42; color: var(--muted); max-width: 165mm; margin: 0 auto; break-before: avoid; page-break-before: avoid; }
figcaption strong { color: var(--ink); }
"""


def make_crops() -> None:
    from PIL import Image  # noqa: PLC0415

    shots = DOCS / "screenshots"
    out = HERE / "img"
    out.mkdir(exist_ok=True)
    for dst, (src, box) in CROPS.items():
        Image.open(shots / src).convert("RGB").crop(box).save(out / dst, optimize=True)
        print("crop", dst)


def build_html() -> str:
    text = MD.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["extra", "sane_lists"], output_format="html5")

    # Относительные ссылки на файлы репозитория — в PDF как выделенный текст
    body = re.sub(r'<a href="(?!https?://)[^"]*">(.*?)</a>', r'<span class="ref">\1</span>', body, flags=re.S)

    # Абзац с картинками + следующий абзац-подпись «Рис. N…» → <figure>
    def figure(m: re.Match) -> str:
        imgs_html, caption = m.group(1), m.group(2)
        srcs = re.findall(r'<img[^>]*src="([^"]+)"[^>]*>', imgs_html)
        alts = re.findall(r'<img[^>]*alt="([^"]*)"', imgs_html)
        parts = []
        for i, src in enumerate(srcs):
            alt = alts[i] if i < len(alts) else ""
            for repl in FIGURES.get(src, [src]):
                parts.append(f'<img src="{repl}" alt="{html.escape(alt)}">')
        if len(srcs) > 1:
            cls = "shots small" if all("quick-actions" in s for s in srcs) else "shots"
            inner = f'<div class="{cls}">{"".join(parts)}</div>'
        else:
            inner = "".join(parts)
        keep = ' class="keep"' if len(parts) == 1 or len(srcs) > 1 else ""
        return f"<figure{keep}>{inner}<figcaption>{caption}</figcaption></figure>"

    body = re.sub(r"<p>((?:\s*<img[^>]+>\s*)+)</p>\s*<p><em>(Рис\. .*?)</em></p>", figure, body, flags=re.S)

    # Разрывы страниц перед крупными разделами
    def h2(m: re.Match) -> str:
        title = re.sub(r"<[^>]+>", "", m.group(1))
        cls = ' class="break"' if title.startswith(PAGE_BREAK_BEFORE) else ""
        return f"<h2{cls}>{m.group(1)}</h2>"

    body = re.sub(r"<h2>(.*?)</h2>", h2, body)

    # Обложка: заголовок + метаданные; блок «Коротко» в рамке
    body = body.replace(
        "<h1>",
        '<div class="cover-kicker">Описание процесса создания с помощью ИИ · ТЗ §10.3</div>\n<h1>',
        1,
    )
    meta = (
        '<div class="cover-meta">'
        "<span>Проект</span><b>«Цифровой деканат будущего» — личный кабинет студента (веб-прототип)</b>"
        "<span>Дата</span><b>22 ноября 2026 г.</b>"
        "<span>Подготовил</span><b>агент-документатор (роль 07), Claude Opus 5.5</b>"
        "<span>Источник фактов</span><b>docs/ai-log/, git log, docs/*.md, код, docs/screenshots/</b>"
        "</div>"
    )
    body = body.replace("</h1>", "</h1>\n" + meta, 1)
    body = re.sub(r"(<h2[^>]*>Коротко</h2>\s*<ul>.*?</ul>)", r'<div class="summary">\1</div>', body, count=1, flags=re.S)

    return (
        "<!DOCTYPE html>\n<html lang=\"ru\"><head><meta charset=\"utf-8\">"
        "<title>Отчёт об использовании ИИ — Цифровой деканат будущего</title>"
        f"<style>{CSS}</style></head><body>\n{body}\n</body></html>\n"
    )


FOOTER = (
    '<div style="width:100%;font-family:\'DejaVu Sans\',sans-serif;font-size:7px;color:#7a8194;'
    'padding:0 15mm;display:flex;justify-content:space-between;">'
    "<span>Цифровой деканат будущего · отчёт об использовании ИИ · концепт для конкурса, не официальный сервис</span>"
    '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
)


def print_pdf() -> None:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME)
        page = browser.new_page()
        page.goto(HTML_OUT.as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.pdf(
            path=str(PDF_OUT),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=FOOTER,
            margin={"top": "15mm", "bottom": "17mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()


def main() -> None:
    if "--crops" in sys.argv:
        make_crops()
    HTML_OUT.write_text(build_html(), encoding="utf-8")
    print("html", HTML_OUT)
    print_pdf()
    print("pdf", PDF_OUT)


if __name__ == "__main__":
    main()
