from django.contrib import admin

from .models import (
    AuditLog,
    Branch,
    Customer,
    Expense,
    InventoryItem,
    LoyaltyTransaction,
    MenuCategory,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    Restaurant,
    RestaurantTable,
    StaffProfile,
    StockMovement,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "restaurant", "status", "order_type", "subtotal", "total_paid", "created_at")
    list_filter = ("status", "order_type", "restaurant")
    search_fields = ("order_number", "customer_name", "customer_phone")
    inlines = [OrderItemInline, PaymentInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "category", "price", "is_available", "is_popular")
    list_filter = ("restaurant", "category", "is_available")
    search_fields = ("name",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant", "current_quantity", "unit", "low_stock_threshold")
    list_filter = ("restaurant",)
    search_fields = ("name",)


admin.site.register(Restaurant)
admin.site.register(Branch)
admin.site.register(StaffProfile)
admin.site.register(RestaurantTable)
admin.site.register(MenuCategory)
admin.site.register(Customer)
admin.site.register(Payment)
admin.site.register(StockMovement)
admin.site.register(Expense)
admin.site.register(LoyaltyTransaction)
admin.site.register(AuditLog)
