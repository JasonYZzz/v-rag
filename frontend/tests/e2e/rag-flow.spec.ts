/**
 * Manual P0-B walkthrough checklist:
 * 1. Start backend from /backend with docker compose up -d or uv run uvicorn app.main:app.
 * 2. Start frontend with pnpm dev.
 * 3. Open /knowledge, upload a text file, confirm it appears with Ready status and chunk count.
 * 4. Open /chat, ask a question, confirm streamed answer and retrieved chunks panel.
 * 5. Open /config and /health, confirm read-only config and backend ok.
 * 6. Press Cmd K or Ctrl K, navigate to all four pages, and switch theme.
 * 7. Check desktop, tablet, and phone widths for usable layout.
 */
export {};
