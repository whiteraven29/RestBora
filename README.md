# RestBora

RestBora is a local restaurant management and QR ordering prototype for Tanzanian restaurants.

## Current Prototype

The current build is a Django + DRF prototype using SQLite. It focuses on the V1 operating flow:

Customer or waiter creates order -> kitchen prepares order -> waiter serves order -> cashier confirms payment -> owner sees reports.

## Run Locally

```bash
python3 manage.py migrate
python3 manage.py seed_demo
python3 manage.py runserver 127.0.0.1:8000
```

Open:

- Owner dashboard: `http://127.0.0.1:8000/`
- Waiter: `http://127.0.0.1:8000/waiter/`
- Kitchen: `http://127.0.0.1:8000/kitchen/`
- Cashier: `http://127.0.0.1:8000/cashier/`
- Inventory/expenses: `http://127.0.0.1:8000/inventory/`
- Public QR menu: `http://127.0.0.1:8000/public/bora-local-foods/menu/`
- API root: `http://127.0.0.1:8000/api/`

Demo users:

- `owner`
- `manager`
- `waiter`
- `kitchen`
- `cashier`

Password for all demo users: `password123`

## Design Docs

- Product scope: `docs/design/00-product-scope.md`
- System architecture: `docs/design/01-system-architecture.md`
- Domain model: `docs/design/02-domain-model.md`
- Order and payment flow: `docs/design/03-order-payment-flow.md`
- API contract: `docs/design/04-api-contract.md`

## Premium Features Parked for Later

Payment gateways, WhatsApp/SMS notifications, advanced loyalty automation, recipe stock deduction, multi-branch UI, native mobile apps, AI recommendations, accounting integrations, and offline mode are intentionally not part of V1.
