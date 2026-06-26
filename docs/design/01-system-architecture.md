# System Architecture

## Current Prototype Choice

The V1 prototype uses Django with Django REST Framework and SQLite. This keeps the backend close to the intended production stack while avoiding unnecessary setup before the workflow is validated.

## Target Production Stack

- Backend: Django, Django REST Framework
- Auth: session auth for prototype, JWT for production API clients
- Database: PostgreSQL in production, SQLite for local prototype
- Async jobs: Celery and Redis later, only when notifications/background work are introduced
- Frontend: React/Vite admin app later; server-rendered prototype screens now
- Public ordering: mobile-friendly web page, later can move to Next.js if SEO/public marketing pages matter

## Boundaries

- `config`: Django project settings and root routing
- `core`: MVP business domain for restaurant operations
- `docs/design`: system design decisions
- `docs/tasks`: implementation task breakdowns

## Prototype Screens

- `/` owner dashboard
- `/waiter/` waiter order entry
- `/kitchen/` kitchen display
- `/cashier/` unpaid orders and payment action
- `/inventory/` stock and expenses overview
- `/public/<restaurant_slug>/menu/` QR customer menu

## API Shape

The prototype exposes REST-style endpoints under `/api/`. These are intentionally simple and will become the contract for the later React frontend.
