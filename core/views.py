from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Branch,
    Customer,
    Expense,
    InventoryItem,
    MenuCategory,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    Restaurant,
    RestaurantTable,
    StockMovement,
)


def get_restaurant():
    return Restaurant.objects.first()


def dashboard(request):
    restaurant = get_restaurant()
    today = timezone.localdate()
    orders = Order.objects.filter(restaurant=restaurant, created_at__date=today) if restaurant else Order.objects.none()
    paid_orders = orders.filter(status=Order.Status.PAID)
    expenses = Expense.objects.filter(restaurant=restaurant, expense_date=today) if restaurant else Expense.objects.none()
    today_sales = paid_orders.aggregate(total=Sum("subtotal"))["total"] or Decimal("0.00")
    today_expenses = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    food_costs = paid_orders.aggregate(total=Sum("estimated_food_cost_total"))["total"] or Decimal("0.00")
    best_items = (
        OrderItem.objects.filter(order__restaurant=restaurant)
        .values("item_name")
        .annotate(quantity=Sum("quantity"), sales=Sum("line_total"))
        .order_by("-quantity")[:5]
        if restaurant
        else []
    )
    recent_orders = (
        Order.objects.filter(restaurant=restaurant)
        .select_related("table", "customer")
        .prefetch_related("items")
        .order_by("-created_at")[:6]
        if restaurant
        else []
    )
    top_customers = (
        Customer.objects.filter(restaurant=restaurant)
        .order_by("-total_spending", "-total_orders")[:4]
        if restaurant
        else []
    )
    status_counts = {
        "pending": orders.filter(status=Order.Status.PENDING).count(),
        "preparing": orders.filter(status=Order.Status.PREPARING).count(),
        "ready": orders.filter(status=Order.Status.READY).count(),
        "served": orders.filter(status=Order.Status.SERVED).count(),
    }
    context = {
        "restaurant": restaurant,
        "today": today,
        "today_sales": today_sales,
        "total_orders": orders.count(),
        "paid_orders": paid_orders.count(),
        "unpaid_orders": orders.exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED]).count(),
        "cancelled_orders": orders.filter(status=Order.Status.CANCELLED).count(),
        "today_expenses": today_expenses,
        "estimated_profit": today_sales - today_expenses - food_costs,
        "low_stock": [item for item in InventoryItem.objects.filter(restaurant=restaurant) if item.is_low_stock] if restaurant else [],
        "active_orders": Order.objects.filter(restaurant=restaurant).exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])[:8] if restaurant else [],
        "best_items": best_items,
        "recent_orders": recent_orders,
        "top_customers": top_customers,
        "status_counts": status_counts,
    }
    return render(request, "core/dashboard.html", context)


def waiter_screen(request):
    restaurant = get_restaurant()
    context = {
        "restaurant": restaurant,
        "tables": RestaurantTable.objects.filter(restaurant=restaurant, is_active=True) if restaurant else [],
        "items": MenuItem.objects.filter(restaurant=restaurant, is_available=True) if restaurant else [],
        "orders": Order.objects.filter(restaurant=restaurant).exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])[:10] if restaurant else [],
    }
    return render(request, "core/waiter.html", context)


@require_POST
def create_waiter_order(request):
    restaurant = get_object_or_404(Restaurant, pk=request.POST["restaurant"])
    branch = Branch.objects.filter(restaurant=restaurant).first()
    table = RestaurantTable.objects.filter(pk=request.POST.get("table"), restaurant=restaurant).first()
    order = Order.objects.create(
        restaurant=restaurant,
        branch=branch,
        table=table,
        order_type=Order.OrderType.DINE_IN,
        customer_name=request.POST.get("customer_name", ""),
        notes=request.POST.get("notes", ""),
    )
    for item in MenuItem.objects.filter(restaurant=restaurant, is_available=True):
        quantity = int(request.POST.get(f"item_{item.id}", "0") or 0)
        if quantity > 0:
            OrderItem.objects.create(
                order=order,
                menu_item=item,
                item_name=item.name,
                quantity=quantity,
                unit_price=item.price,
                estimated_unit_food_cost=item.estimated_food_cost,
            )
    if order.items.count() == 0:
        order.delete()
        messages.error(request, "Select at least one item before sending an order.")
    else:
        messages.success(request, f"Order {order.order_number} sent to kitchen.")
    return redirect("waiter")


def kitchen_screen(request):
    restaurant = get_restaurant()
    orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=[Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.PREPARING, Order.Status.READY],
    ) if restaurant else []
    return render(request, "core/kitchen.html", {"restaurant": restaurant, "orders": orders, "statuses": Order.Status})


@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    order.status = request.POST["status"]
    order.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Order {order.order_number} moved to {order.get_status_display()}.")
    return redirect(request.POST.get("next", "dashboard"))


def cashier_screen(request):
    restaurant = get_restaurant()
    orders = Order.objects.filter(restaurant=restaurant).exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED]) if restaurant else []
    return render(request, "core/cashier.html", {"restaurant": restaurant, "orders": orders, "methods": Payment.Method})


@require_POST
def record_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    Payment.objects.create(
        order=order,
        method=request.POST["method"],
        amount=Decimal(request.POST["amount"]),
        reference=request.POST.get("reference", ""),
    )
    if order.customer and order.status == Order.Status.PAID:
        order.customer.total_spending = Customer.objects.get(pk=order.customer_id).total_spending
    messages.success(request, f"Payment recorded for {order.order_number}.")
    return redirect("cashier")


def inventory_screen(request):
    restaurant = get_restaurant()
    return render(
        request,
        "core/inventory.html",
        {
            "restaurant": restaurant,
            "items": InventoryItem.objects.filter(restaurant=restaurant) if restaurant else [],
            "expenses": Expense.objects.filter(restaurant=restaurant)[:10] if restaurant else [],
            "movement_types": StockMovement.MovementType,
            "expense_categories": Expense.Category,
        },
    )


@require_POST
def add_stock_movement(request, item_id):
    item = get_object_or_404(InventoryItem, pk=item_id)
    StockMovement.objects.create(
        item=item,
        movement_type=request.POST["movement_type"],
        quantity=Decimal(request.POST["quantity"]),
        unit_cost=Decimal(request.POST.get("unit_cost") or "0"),
        note=request.POST.get("note", ""),
    )
    messages.success(request, f"Stock updated for {item.name}.")
    return redirect("inventory")


@require_POST
def add_expense(request):
    restaurant = get_object_or_404(Restaurant, pk=request.POST["restaurant"])
    Expense.objects.create(
        restaurant=restaurant,
        category=request.POST["category"],
        amount=Decimal(request.POST["amount"]),
        expense_date=request.POST.get("expense_date") or timezone.localdate(),
        note=request.POST.get("note", ""),
    )
    messages.success(request, "Expense recorded.")
    return redirect("inventory")


def public_menu_screen(request, slug):
    restaurant = get_object_or_404(Restaurant, slug=slug)
    table = RestaurantTable.objects.filter(restaurant=restaurant, qr_token=request.GET.get("table")).first()
    categories = MenuCategory.objects.filter(restaurant=restaurant, is_active=True)
    items = MenuItem.objects.filter(restaurant=restaurant, is_available=True)
    return render(request, "core/public_menu.html", {"restaurant": restaurant, "table": table, "categories": categories, "items": items})


@require_POST
def create_public_order(request, slug):
    restaurant = get_object_or_404(Restaurant, slug=slug)
    branch = Branch.objects.filter(restaurant=restaurant).first()
    table = RestaurantTable.objects.filter(restaurant=restaurant, qr_token=request.POST.get("table_token")).first()
    phone = request.POST.get("customer_phone", "").strip()
    name = request.POST.get("customer_name", "").strip() or "Guest"
    customer = None
    if phone:
        customer, _ = Customer.objects.get_or_create(restaurant=restaurant, phone=phone, defaults={"name": name})
        customer.name = name
        customer.last_order_at = timezone.now()
        customer.save(update_fields=["name", "last_order_at", "updated_at"])
    order = Order.objects.create(
        restaurant=restaurant,
        branch=branch,
        table=table,
        customer=customer,
        customer_name=name,
        customer_phone=phone,
        order_type=Order.OrderType.QR_TABLE if table else Order.OrderType.TAKEAWAY,
        notes=request.POST.get("notes", ""),
    )
    for item in MenuItem.objects.filter(restaurant=restaurant, is_available=True):
        quantity = int(request.POST.get(f"item_{item.id}", "0") or 0)
        if quantity > 0:
            OrderItem.objects.create(
                order=order,
                menu_item=item,
                item_name=item.name,
                quantity=quantity,
                unit_price=item.price,
                estimated_unit_food_cost=item.estimated_food_cost,
            )
    if order.items.count() == 0:
        order.delete()
        messages.error(request, "Please select at least one item.")
        return redirect("public-menu", slug=slug)
    if customer:
        customer.total_orders += 1
        customer.total_spending += order.subtotal
        customer.last_order_at = timezone.now()
        customer.loyalty_points += 1
        customer.save(update_fields=["total_orders", "total_spending", "last_order_at", "loyalty_points", "updated_at"])
    return render(request, "core/order_success.html", {"restaurant": restaurant, "order": order})
