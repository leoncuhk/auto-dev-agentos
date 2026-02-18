# Todo App — Project Specification

## Overview

Build a minimal but complete **Todo List web application** with a Node.js backend and vanilla HTML/CSS/JS frontend. No external frameworks required — keep it simple and self-contained.

## Tech Stack

- **Backend**: Node.js (built-in `http` module or Express)
- **Frontend**: Vanilla HTML + CSS + JavaScript (no React, no build tools)
- **Storage**: JSON file on disk (`data/todos.json`) — no database needed
- **Testing**: Node.js built-in `node --test` or a simple test script

## Features

### F1: View all todos
- GET `/` serves the main HTML page
- Page displays a list of all todo items
- Each item shows: title, completion status (checkbox), delete button

### F2: Add a new todo
- Input field at top of page with "Add" button
- POST `/api/todos` creates a new todo with `title` and `completed: false`
- Page updates immediately without full reload (use fetch)

### F3: Toggle todo completion
- Clicking the checkbox toggles `completed` status
- PATCH `/api/todos/:id` updates the todo
- Visual distinction between completed and pending items (strikethrough)

### F4: Delete a todo
- Clicking the delete button (✕) removes the item
- DELETE `/api/todos/:id` removes from storage
- Item disappears from the list

### F5: Persistent storage
- Todos survive server restart (stored in `data/todos.json`)
- Server creates the file automatically if it doesn't exist

### F6: Clean responsive UI
- Centered layout, max-width 600px
- Clean fonts, subtle colors
- Works on mobile and desktop
- Hover effects on interactive elements

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve the HTML page |
| GET | `/api/todos` | List all todos |
| POST | `/api/todos` | Create a todo (`{ "title": "..." }`) |
| PATCH | `/api/todos/:id` | Update a todo (`{ "completed": true }`) |
| DELETE | `/api/todos/:id` | Delete a todo |

## Data Model

```json
{
  "id": "uuid-string",
  "title": "Buy groceries",
  "completed": false,
  "created_at": "2025-01-01T00:00:00Z"
}
```

## File Structure (expected output)

```
todo-app/
├── server.js          # Main server entry point
├── public/
│   ├── index.html     # Main page
│   ├── style.css      # Styles
│   └── app.js         # Client-side JavaScript
├── data/
│   └── todos.json     # Persistent storage (auto-created)
├── package.json
└── test/
    └── api.test.js    # Basic API tests
```

## Quality Requirements

- Server starts with `npm start` (or `node server.js`)
- All API endpoints return proper JSON with correct HTTP status codes
- Input validation: reject empty titles
- Tests can be run with `npm test`
- No external dependencies beyond Express (if used)

