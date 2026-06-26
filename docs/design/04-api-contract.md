# API Contract

## Auth

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`

## Restaurant

- `GET /api/restaurants/me/`
- `PUT /api/restaurants/me/update/`

## Menu

- `GET /api/menu/categories/`
- `POST /api/menu/categories/`
- `GET /api/menu/items/`
- `POST /api/menu/items/`
- `PATCH /api/menu/items/{id}/availability/`

## Tables

- `GET /api/tables/`
- `POST /api/tables/`
- `GET /api/tables/{id}/qr/`

## Orders

- `GET /api/orders/`
- `POST /api/orders/`
- `GET /api/orders/kitchen/`
- `GET /api/orders/unpaid/`
- `PATCH /api/orders/{id}/status/`
- `PATCH /api/orders/{id}/cancel/`

## Public QR Ordering

- `GET /api/public/restaurants/{slug}/menu/`
- `POST /api/public/restaurants/{slug}/orders/`
- `GET /api/public/orders/{order_number}/status/`

## Payments, Inventory, Expenses, Reports

- `POST /api/payments/`
- `GET /api/payments/daily-summary/`
- `GET /api/inventory/`
- `POST /api/inventory/{id}/movement/`
- `GET /api/inventory/low-stock/`
- `GET /api/expenses/`
- `POST /api/expenses/`
- `GET /api/reports/dashboard/`
- `GET /api/reports/profit-loss/`
