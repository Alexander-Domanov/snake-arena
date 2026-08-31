# Product Specification: Interview Canvas (MVP)

## Overview
A collaborative whiteboard for system design interviews. Participants can draw diagrams, add sticky notes, and view the board. This MVP focuses on REST API, frontend, and SQLite persistence. Real-time updates will be added later.

## User Stories
1. **As a user**, I want to create a new board and get a unique ID.
2. **As a user**, I want to join a board by its ID and see all existing elements.
3. **As a user**, I want to add a sticky note with text at a specific position.
4. **As a user**, I want to add a shape (rectangle or circle) at a specific position with size.
5. **As a user**, I want to delete an element I created.

## Acceptance Criteria
- [x] POST /boards returns a new board with a unique ID.
- [x] GET /boards/{id} returns the board with all its elements.
- [x] POST /boards/{id}/elements adds a sticky note or shape and returns the created element.
- [x] DELETE /elements/{id} removes the element from the board.
- [x] All data is persisted in SQLite.
- [x] Frontend (HTML/CSS/JS) can call these endpoints and display the board.
- [x] Frontend joins a board by link (?board=<id>): opens that board instead of creating a new one, and shows the shareable link in the toolbar.

## Non-goals (for Module 2)
- No real-time WebSocket (will be added in Module 3).
- No user authentication.
- No advanced drawing (only sticky notes, rectangles, circles).
- No undo/redo.

## Tech Stack
- Frontend: HTML + CSS + JavaScript (vanilla)
- Backend: FastAPI (Python)
- Database: SQLite with SQLAlchemy
- API Contract: OpenAPI 3.0 (openapi.yaml)
- Testing: pytest
- Dependencies: uv
