# StudyNest
A simple student study log and weekly timetable using Flask and SQLite.

## Run on Windows (VS Code terminal)
1. `python -m venv .venv`
2. Activate with `.venv\Scripts\activate` (Command Prompt) or `.venv\Scripts\Activate.ps1` (PowerShell).
3. `pip install -r requirements.txt`
4. `python app.py`
5. Open http://127.0.0.1:5000

SQLite database `studynest.db` is created automatically when the app starts.

## Included
- Register, login, logout (password hashes).
- Personal study session log: subject, date, minutes, optional note; add and delete.
- Weekly timetable: weekday, subject and time range; add and delete.
- Personal totals; data is separated per registered user.

## Notes
- This is a learning/demo project, not production-ready authentication infrastructure.
- Before public deployment set a strong `SECRET_KEY` environment variable; do not use the development fallback in production.
- Back up `studynest.db` if you want to retain data.
- Static assets use Google Fonts when the browser is online, with system-font fallback.
