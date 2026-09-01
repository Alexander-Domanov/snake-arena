"""End-to-end: two sessions share a board (reload-based sync, no WebSocket).

Scenario (adapted from the article's two-session test — this app has no
real-time updates, so the interviewer verifies changes after a reload):

1. Interviewer opens the app -> a board is created, share link is shown
2. Candidate opens the share link in a separate browser context
3. Candidate adds a sticky note
4. Interviewer reloads and sees the sticky note (server is source of truth)
5. Candidate deletes the sticky note
6. Interviewer reloads and sees it is gone

Requires the docker-compose stack running on E2E_BASE_URL (default
http://localhost:8100):

    docker compose up -d

Run with:

    uv run pytest e2e -v
"""
import os
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8100")


def test_candidate_change_visible_to_interviewer_after_reload(browser):
    interviewer = browser.new_context()
    candidate = browser.new_context()
    try:
        page1 = interviewer.new_page()
        page2 = candidate.new_page()

        # 1. interviewer creates a board; the share link appears in the toolbar
        page1.goto(BASE_URL + "/")
        expect(page1.locator("#board-link")).to_have_value(re.compile(r"board="))
        link = page1.input_value("#board-link")
        assert link.startswith(BASE_URL), f"share link should point at the app, got {link}"

        # 2. candidate joins the same board by link (no new board is created)
        page2.goto(link)
        expect(page2.locator("#board-link")).to_have_value(link)
        expect(page2.locator(".el")).to_have_count(0)

        # 3. candidate adds a sticky note
        page2.click("#btn-sticky")
        expect(page2.locator(".el")).to_have_count(1)

        # 4. interviewer reloads and sees the candidate's sticky note
        page1.reload()
        expect(page1.locator("#board-link")).to_have_value(re.compile(r"board="))
        expect(page1.locator(".el")).to_have_count(1)

        # 5. candidate deletes the sticky note (select reveals the delete button)
        page2.locator(".el").click()
        page2.locator(".el .delete-btn").click()
        expect(page2.locator(".el")).to_have_count(0)

        # 6. interviewer reloads and sees the deletion
        page1.reload()
        expect(page1.locator(".el")).to_have_count(0)
    finally:
        interviewer.close()
        candidate.close()
