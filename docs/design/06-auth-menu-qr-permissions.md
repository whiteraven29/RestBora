# Auth, Menu, and QR Permissions

## Staff Login

All staff-account dashboards require login. After login, users are redirected by role:

- Owner and manager: owner dashboard
- Waiter: waiter order screen
- Kitchen: kitchen display
- Cashier: cashier payment screen

## Menu/Food Management

Food items belong to one restaurant. The following roles can add foods:

- Owner
- Manager
- Kitchen

Allowed actions:

- Add menu categories
- Add menu items
- Set price
- Set estimated food cost
- Set preparation time
- Mark item as available/unavailable
- Mark item as popular

## Table QR Generation

Only owner and manager accounts can create tables and generate table QR codes.

Generated QR codes point to:

`/public/<restaurant-slug>/menu/?table=<table-token>`

Customers who scan the QR code can place an order without login.

## Public QR Ordering

Public QR ordering remains unauthenticated in V1. Customers provide name and phone number at order time for customer records and basic loyalty tracking.
