from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api, views

router = DefaultRouter()
router.register("restaurants", api.RestaurantViewSet)
router.register("staff", api.StaffViewSet)
router.register("menu/categories", api.MenuCategoryViewSet)
router.register("menu/items", api.MenuItemViewSet)
router.register("tables", api.TableViewSet)
router.register("orders", api.OrderViewSet)
router.register("payments", api.PaymentViewSet)
router.register("inventory", api.InventoryItemViewSet)
router.register("expenses", api.ExpenseViewSet)
router.register("customers", api.CustomerViewSet)

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("waiter/", views.waiter_screen, name="waiter"),
    path("waiter/orders/", views.create_waiter_order, name="create-waiter-order"),
    path("kitchen/", views.kitchen_screen, name="kitchen"),
    path("orders/<int:order_id>/status/", views.update_order_status, name="update-order-status"),
    path("cashier/", views.cashier_screen, name="cashier"),
    path("cashier/orders/<int:order_id>/payments/", views.record_payment, name="record-payment"),
    path("inventory/", views.inventory_screen, name="inventory"),
    path("inventory/<int:item_id>/movement/", views.add_stock_movement, name="add-stock-movement"),
    path("expenses/", views.add_expense, name="add-expense"),
    path("public/<slug:slug>/menu/", views.public_menu_screen, name="public-menu"),
    path("public/<slug:slug>/orders/", views.create_public_order, name="create-public-order"),
    path("api/auth/register/", api.register, name="api-register"),
    path("api/auth/login/", api.login_view, name="api-login"),
    path("api/auth/logout/", api.logout_view, name="api-logout"),
    path("api/public/restaurants/<slug:slug>/menu/", api.public_menu, name="api-public-menu"),
    path("api/public/restaurants/<slug:slug>/orders/", api.public_order, name="api-public-order"),
    path("api/public/orders/<str:order_number>/status/", api.public_order_status, name="api-public-order-status"),
    path("api/reports/dashboard/", api.dashboard_report, name="api-dashboard-report"),
    path("api/reports/profit-loss/", api.profit_loss_report, name="api-profit-loss-report"),
    path("api/", include(router.urls)),
]
