# Order and Payment Flow

## Status Lifecycle

1. `pending`: order has been submitted.
2. `accepted`: staff confirms it should go to the kitchen.
3. `preparing`: kitchen has started preparing it.
4. `ready`: kitchen says it is ready for service.
5. `served`: waiter has served the customer.
6. `paid`: cashier has confirmed full payment.
7. `cancelled`: order was cancelled with a reason.

## Waiter Flow

1. Select table.
2. Select menu items and quantities.
3. Add optional notes.
4. Submit order.
5. Follow kitchen status.
6. Mark ready orders as served.

## Customer QR Flow

1. Scan table QR code.
2. View available menu.
3. Select items.
4. Enter name and phone number.
5. Submit order.
6. Receive order number.

## Cashier Flow

1. View unpaid served/ready orders.
2. Select payment method.
3. Record amount and optional reference.
4. Confirm payment.
5. Order becomes `paid` once total paid covers order total.
