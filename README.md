# College Attendance Website (Python)

A complete web app to manage college attendance with:

- Login system (Admin and Teacher roles)
- Student management
- Course management
- Student enrollment into courses
- Daily attendance marking (present/absent)
- Per-course attendance reports
- CSV export for course reports
- Monthly attendance summary page

## Tech Stack

- Python
- Flask
- SQLite
- Flask-Login
- Flask-SQLAlchemy

## Setup

1. Open terminal in this project folder.
2. Create and activate virtual environment:

   On Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Run app:

   ```powershell
   python app.py
   ```

5. Open in browser:

   http://127.0.0.1:5000

## Default Login

- Username: `admin`
- Password: `admin123`

Create additional admin/teacher accounts from **Create User** page after login.

## Permanent URL (A.M Gems and Jewellery)

This project includes a Render blueprint file: [render.yaml](render.yaml)

Follow these steps:

1. Push this project to GitHub.
2. Sign in to Render and choose **New +** > **Blueprint**.
3. Select your GitHub repo and deploy.
4. Render will create a permanent URL like:
   - `https://am-gems-and-jewellery.onrender.com`

### Important for data persistence

If you want product and order data to persist after redeploys, create a **Persistent Disk** in Render and set either:

- `AM_GEMS_DATABASE_URL` (full DB URL), or
- `AM_GEMS_DB_PATH` (for SQLite file path, e.g. `/var/data/am_gems.db`)

You can also set:

- `AM_GEMS_SITE_URL` to your final public domain.
