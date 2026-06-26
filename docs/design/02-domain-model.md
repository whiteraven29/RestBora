# Domain Model

## Main Entities

- Restaurant: business profile and default currency
- Branch: supports one branch in V1, leaves room for multi-branch later
- StaffProfile: role and active status for each user
- RestaurantTable: table code, capacity, and QR token
- MenuCategory: menu grouping such as breakfast, lunch, drinks
- MenuItem: price, availability, preparation time, and estimated food cost
- Customer: identified mainly by phone number
- Order: one customer/waiter order and its operational status
- OrderItem: quantity and price snapshot for each food item
- Payment: cashier payment records, including partial payments
- InventoryItem: manually tracked stock item
- StockMovement: stock purchase, usage, spoilage, or adjustment
- Expense: recorded restaurant cost
- LoyaltyTransaction: basic loyalty points and manual adjustments
- AuditLog: important user/system actions

## Important Design Rules

- Order item prices are copied at order time so old reports remain correct after menu price changes.
- Customers do not need accounts in V1. Public QR orders only collect name and phone.
- Stock deduction is manual in V1. Recipe-based automatic deduction belongs in V2/Premium.
- One branch is used in V1, but models include `Branch` so later multi-branch support is not a painful rewrite.
