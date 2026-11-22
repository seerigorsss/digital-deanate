"""Короткий PDF-отчёт для жюри (12 страниц, A4 альбомная): jury.html → docs/jury_report.pdf.

Запуск из корня репозитория: python3 docs/report-build/jury/build_jury.py (нужны playwright и Google Chrome).
Скриншоты телефона в ./img — верхние 780 px (×2) из docs/screenshots/*-mobile.png; остальные — из ../img.
"""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "jury_report.pdf"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME)
    page = browser.new_page()
    page.goto((HERE / "jury.html").as_uri(), wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.pdf(path=str(OUT), width="297mm", height="210mm", print_background=True, prefer_css_page_size=True)
    browser.close()
print("pdf", OUT)
