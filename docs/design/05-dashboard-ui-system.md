# Dashboard UI System

## Source Reference

The internal RestBora dashboards should follow `Dashboard Restaurant (Community).pdf`.

## Design Direction

- Dark restaurant POS interface
- Deep charcoal workspace
- Fixed left sidebar
- Orange/red gradient accents
- Compact rounded cards
- Large operational numbers
- Search and profile controls in the top bar
- Green open-status indicator
- Dense order, kitchen, payment, and inventory panels

## Applied To V1 Internal Screens

- Staff account login
- Owner dashboard
- Waiter order screen
- Kitchen display
- Cashier payment screen
- Inventory and expenses screen

## Production Rule

All authenticated staff dashboards should use the shared internal shell in `templates/core/internal_base.html`. Avoid creating new dashboard layouts from scratch. New role screens should extend that template and provide:

- `internal_title`
- `internal_subtitle`
- one active navigation block
- role-specific content inside `internal_content`

## Customer QR Exception

The public customer QR ordering page can use a simpler mobile-first customer style. Customers are not staff-account users in V1, so the internal dark POS dashboard shell is not required there.
