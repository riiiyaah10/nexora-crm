# CRM-ERP (Django)

OTP email login · Dashboard · Leads (pipeline + board + activity log + CSV export) · Projects · Finance (invoices with GST,
income/expenses, monthly chart) · Roles & per-user permissions · **Access Denied** page · Audit log · Tasks/follow-ups.

## Run in VS Code
    python -m venv venv
    venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
    pip install -r requirements.txt
    copy .env.example .env           # macOS/Linux: cp .env.example .env
    python manage.py migrate
    python manage.py seed --admin-email you@yourmail.com
    python manage.py runserver
Open http://127.0.0.1:8000 → enter an email → the **OTP is printed in the terminal** (dev mode).
(Optional) `python manage.py createsuperuser` if you also want the Django /admin/ site with a password.

## Demo users (from `seed`; use --no-demo to skip them and the sample data)
| Email | Role | Can open |
|---|---|---|
| your admin email | Admin | everything + Users, Roles, Audit log |
| sales@example.com | Sales | Dashboard, own Leads |
| salesmgr@example.com | Sales Manager | Dashboard, ALL leads, Projects (view) |
| pm@example.com | Project Manager | Dashboard, Projects, Leads (view) |
| finance@example.com | Finance | Dashboard, Finance, Projects (view) |
Everything else shows **Access Denied**.

## How access control works
* Roles = Django **Groups**; permissions = Django permissions (catalogue in `accounts/permissions.py`).
* Users & Roles pages (admin only) let you create users, change roles, edit each role's permissions, and give a single
  user **extra permissions** beyond their role.
* Protect any view with `@perm_required("app.codename")` or `PermMixin` (`core/permissions.py`) → 403 → `templates/403.html`.
* Sidebar/buttons are hidden with `{% if perms.leads.add_lead %}` in templates.
* Sales users see only leads they own unless they have "See ALL leads".
* "Convert lead to project" needs both *Edit leads* and *Add projects*.

## MySQL
Uncomment the DB_* lines in `.env`, create the database (`CREATE DATABASE crm_erp CHARACTER SET utf8mb4;`), then migrate.

## Real OTP emails
Fill EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD in `.env` (Gmail: use an App Password).

## Layout
    config/    settings, urls          accounts/  User, OTP login, users/roles/audit pages, seed command
    core/      dashboard, tasks, audit  leads/     leads, activities, board, CSV export, convert
    projects/  projects                 finance/   invoices, income/expenses, summaries
    templates/ all pages                static/css/app.css

## Ideas to build next
Email/WhatsApp reminders for follow-ups · lead import from CSV/Excel · invoice PDF · REST API (Django REST Framework)
· contacts/companies as separate records · file attachments · deployment (gunicorn + nginx, DEBUG=0, MySQL).
