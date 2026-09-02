"""End-to-end: two sessions share a board (reload-based sync, no WebSocket).

Scenario (adapted from the article's two-session test — this app has no
real-time updates, so the interviewer verifies changes after a reload):

1. Interviewer opens the app -> a board is created, share link is shown
2. Candidate opens the share link in a separate browser context
3. Candidate adds a sticky note
4. Candidate edits the sticky text (double-click, type, blur) and drags it
5. Interviewer reloads and sees the edited text AND the new position
   (persistent editing: PATCH /elements/{id} saved both)
6. Candidate deletes the sticky note
7. Interviewer reloads and sees it is gone

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

NEW_TEXT = "Persistent editing works"
MOVE_DX = 140
MOVE_DY = 90
POS_TOLERANCE = 3  # px: bounding boxes may differ by sub-pixel rounding


def assert_position_near(actual: dict, expected: dict, tolerance: float = POS_TOLERANCE) -> None:
    assert actual is not None and expected is not None
    assert abs(actual["x"] - expected["x"]) <= tolerance, f"x differs: {actual} vs {expected}"
    assert abs(actual["y"] - expected["y"]) <= tolerance, f"y differs: {actual} vs {expected}"


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
        sticky = page2.locator(".el.sticky")
        expect(sticky).to_be_visible()

        # 4a. candidate edits the text: dblclick -> replace -> blur (fires PATCH)
        note_body = page2.locator(".el.sticky .note-body")
        note_body.dblclick()
        expect(note_body).to_have_attribute("contenteditable", "true")
        page2.keyboard.press("Meta+A")
        page2.keyboard.type(NEW_TEXT)

        # blur by clicking empty board space -> stopEditing sends PATCH {text}
        with page2.expect_response(
            lambda r: r.request.method == "PATCH" and "/elements/" in r.url
        ) as text_patch:
            page2.mouse.click(10, 10)
        assert text_patch.value.status == 200
        # local UI already shows the new text
        expect(note_body).to_have_text(NEW_TEXT)

        # 4b. candidate drags the sticky note to a new position
        before = sticky.bounding_box()
        assert before is not None
        with page2.expect_response(
            lambda r: r.request.method == "PATCH" and "/elements/" in r.url
        ) as move_patch:
            page2.mouse.move(before["x"] + before["width"] / 2, before["y"] + before["height"] / 2)
            page2.mouse.down()
            page2.mouse.move(
                before["x"] + before["width"] / 2 + MOVE_DX,
                before["y"] + before["height"] / 2 + MOVE_DY,
                steps=8,
            )
            page2.mouse.up()
        assert move_patch.value.status == 200
        moved_box = sticky.bounding_box()
        assert moved_box is not None
        assert_position_near(moved_box, {"x": before["x"] + MOVE_DX, "y": before["y"] + MOVE_DY})

        # 5. interviewer reloads: sees the note AND its persisted text and position
        page1.reload()
        expect(page1.locator("#board-link")).to_have_value(re.compile(r"board="))
        expect(page1.locator(".el")).to_have_count(1)
        expect(page1.locator(".el.sticky .note-body")).to_have_text(NEW_TEXT)
        interviewer_box = page1.locator(".el.sticky").bounding_box()
        assert_position_near(interviewer_box, moved_box)

        # 6. candidate deletes the sticky note (select reveals the delete button)
        page2.locator(".el").click()
        page2.locator(".el .delete-btn").click()
        expect(page2.locator(".el")).to_have_count(0)

        # 7. interviewer reloads and sees the deletion
        page1.reload()
        expect(page1.locator(".el")).to_have_count(0)
    finally:
        interviewer.close()
        candidate.close()
