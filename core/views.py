from decimal import Decimal
from io import BytesIO

import qrcode
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
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
    StaffProfile,
    StockMovement,
)


class StaffLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        profile = get_staff_profile(self.request.user)
        if not profile:
            return "/"
        if profile.role in [StaffProfile.Role.OWNER, StaffProfile.Role.MANAGER]:
            return "/"
        if profile.role == StaffProfile.Role.WAITER:
            return "/waiter/"
        if profile.role == StaffProfile.Role.KITCHEN:
            return "/kitchen/"
        if profile.role == StaffProfile.Role.CASHIER:
            return "/cashier/"
        return "/"


def get_restaurant():
    return Restaurant.objects.first()


def get_staff_profile(user):
    return getattr(user, "staff_profile", None)


def get_user_restaurant(user):
    profile = get_staff_profile(user)
    return profile.restaurant if profile else get_restaurant()


def require_staff_role(user, allowed_roles):
    profile = get_staff_profile(user)
    if not profile or not profile.is_active or profile.role not in allowed_roles:
        raise PermissionDenied("You do not have permission to access this page.")
    return profile


def staff_context(request, restaurant=None):
    profile = get_staff_profile(request.user)
    return {
        "restaurant": restaurant or get_user_restaurant(request.user),
        "staff_profile": profile,
    }


@login_required
def dashboard(request):
    require_staff_role(request.user, ["owner", "manager"])
    restaurant = get_user_restaurant(request.user)
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
        **staff_context(request, restaurant),
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


@login_required
def waiter_screen(request):
    require_staff_role(request.user, ["owner", "manager", "waiter"])
    restaurant = get_user_restaurant(request.user)
    context = {
        **staff_context(request, restaurant),
        "tables": RestaurantTable.objects.filter(restaurant=restaurant, is_active=True) if restaurant else [],
        "items": MenuItem.objects.filter(restaurant=restaurant, is_available=True) if restaurant else [],
        "orders": Order.objects.filter(restaurant=restaurant).exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])[:10] if restaurant else [],
    }
    return render(request, "core/waiter.html", context)


@require_POST
@login_required
def create_waiter_order(request):
    require_staff_role(request.user, ["owner", "manager", "waiter"])
    restaurant = get_user_restaurant(request.user)
    branch = Branch.objects.filter(restaurant=restaurant).first()
    table = RestaurantTable.objects.filter(pk=request.POST.get("table"), restaurant=restaurant).first()
    order = Order.objects.create(
        restaurant=restaurant,
        branch=branch,
        table=table,
        order_type=Order.OrderType.DINE_IN,
        customer_name=request.POST.get("customer_name", ""),
        notes=request.POST.get("notes", ""),
        waiter=request.user,
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


@login_required
def kitchen_screen(request):
    require_staff_role(request.user, ["owner", "manager", "kitchen"])
    restaurant = get_user_restaurant(request.user)
    orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=[Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.PREPARING, Order.Status.READY],
    ) if restaurant else []
    return render(request, "core/kitchen.html", {**staff_context(request, restaurant), "orders": orders, "statuses": Order.Status})


@require_POST
@login_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    profile = require_staff_role(request.user, ["owner", "manager", "waiter", "kitchen"])
    if order.restaurant_id != profile.restaurant_id:
        raise PermissionDenied("This order belongs to another restaurant.")
    order.status = request.POST["status"]
    order.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Order {order.order_number} moved to {order.get_status_display()}.")
    return redirect(request.POST.get("next", "dashboard"))


@login_required
def cashier_screen(request):
    require_staff_role(request.user, ["owner", "manager", "cashier"])
    restaurant = get_user_restaurant(request.user)
    orders = Order.objects.filter(restaurant=restaurant).exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED]) if restaurant else []
    return render(request, "core/cashier.html", {**staff_context(request, restaurant), "orders": orders, "methods": Payment.Method})


@require_POST
@login_required
def record_payment(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    profile = require_staff_role(request.user, ["owner", "manager", "cashier"])
    if order.restaurant_id != profile.restaurant_id:
        raise PermissionDenied("This order belongs to another restaurant.")
    Payment.objects.create(
        order=order,
        method=request.POST["method"],
        amount=Decimal(request.POST["amount"]),
        reference=request.POST.get("reference", ""),
        received_by=request.user,
    )
    if order.customer and order.status == Order.Status.PAID:
        order.customer.total_spending = Customer.objects.get(pk=order.customer_id).total_spending
    messages.success(request, f"Payment recorded for {order.order_number}.")
    return redirect("cashier")


@login_required
def inventory_screen(request):
    require_staff_role(request.user, ["owner", "manager", "kitchen"])
    restaurant = get_user_restaurant(request.user)
    return render(
        request,
        "core/inventory.html",
        {
            **staff_context(request, restaurant),
            "items": InventoryItem.objects.filter(restaurant=restaurant) if restaurant else [],
            "expenses": Expense.objects.filter(restaurant=restaurant)[:10] if restaurant else [],
            "movement_types": StockMovement.MovementType,
            "expense_categories": Expense.Category,
        },
    )


@require_POST
@login_required
def add_stock_movement(request, item_id):
    item = get_object_or_404(InventoryItem, pk=item_id)
    profile = require_staff_role(request.user, ["owner", "manager", "kitchen"])
    if item.restaurant_id != profile.restaurant_id:
        raise PermissionDenied("This stock item belongs to another restaurant.")
    StockMovement.objects.create(
        item=item,
        movement_type=request.POST["movement_type"],
        quantity=Decimal(request.POST["quantity"]),
        unit_cost=Decimal(request.POST.get("unit_cost") or "0"),
        note=request.POST.get("note", ""),
        recorded_by=request.user,
    )
    messages.success(request, f"Stock updated for {item.name}.")
    return redirect("inventory")


@require_POST
@login_required
def add_expense(request):
    require_staff_role(request.user, ["owner", "manager"])
    restaurant = get_user_restaurant(request.user)
    Expense.objects.create(
        restaurant=restaurant,
        category=request.POST["category"],
        amount=Decimal(request.POST["amount"]),
        expense_date=request.POST.get("expense_date") or timezone.localdate(),
        note=request.POST.get("note", ""),
        recorded_by=request.user,
    )
    messages.success(request, "Expense recorded.")
    return redirect("inventory")


@login_required
def menu_management_screen(request):
    require_staff_role(request.user, ["owner", "manager", "kitchen"])
    restaurant = get_user_restaurant(request.user)
    categories = MenuCategory.objects.filter(restaurant=restaurant)
    items = MenuItem.objects.filter(restaurant=restaurant).select_related("category")
    return render(
        request,
        "core/menu_management.html",
        {
            **staff_context(request, restaurant),
            "categories": categories,
            "items": items,
        },
    )


@require_POST
@login_required
def add_menu_category(request):
    require_staff_role(request.user, ["owner", "manager", "kitchen"])
    restaurant = get_user_restaurant(request.user)
    MenuCategory.objects.get_or_create(
        restaurant=restaurant,
        name=request.POST["name"].strip(),
        defaults={"sort_order": int(request.POST.get("sort_order") or 0), "is_active": True},
    )
    messages.success(request, "Menu category saved.")
    return redirect("menu-management")


@require_POST
@login_required
def add_menu_item(request):
    require_staff_role(request.user, ["owner", "manager", "kitchen"])
    restaurant = get_user_restaurant(request.user)
    category = get_object_or_404(MenuCategory, pk=request.POST["category"], restaurant=restaurant)
    MenuItem.objects.create(
        restaurant=restaurant,
        category=category,
        name=request.POST["name"].strip(),
        description=request.POST.get("description", ""),
        price=Decimal(request.POST["price"]),
        estimated_food_cost=Decimal(request.POST.get("estimated_food_cost") or "0"),
        preparation_minutes=int(request.POST.get("preparation_minutes") or 15),
        is_available=bool(request.POST.get("is_available")),
        is_popular=bool(request.POST.get("is_popular")),
    )
    messages.success(request, "Food item added to the restaurant menu.")
    return redirect("menu-management")


@require_POST
@login_required
def toggle_menu_item_availability(request, item_id):
    require_staff_role(request.user, ["owner", "manager", "kitchen"])
    restaurant = get_user_restaurant(request.user)
    item = get_object_or_404(MenuItem, pk=item_id, restaurant=restaurant)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available", "updated_at"])
    messages.success(request, f"{item.name} availability updated.")
    return redirect("menu-management")


@login_required
def table_qr_screen(request):
    require_staff_role(request.user, ["owner", "manager"])
    restaurant = get_user_restaurant(request.user)
    tables = RestaurantTable.objects.filter(restaurant=restaurant).order_by("label")
    return render(
        request,
        "core/table_qr.html",
        {
            **staff_context(request, restaurant),
            "tables": tables,
        },
    )


@require_POST
@login_required
def add_table(request):
    require_staff_role(request.user, ["owner", "manager"])
    restaurant = get_user_restaurant(request.user)
    branch = Branch.objects.filter(restaurant=restaurant).first()
    label = request.POST["label"].strip()
    token_base = slugify(f"{restaurant.slug}-{label}") or f"table-{RestaurantTable.objects.count() + 1}"
    token = token_base
    counter = 2
    while RestaurantTable.objects.filter(qr_token=token).exists():
        token = f"{token_base}-{counter}"
        counter += 1
    RestaurantTable.objects.get_or_create(
        restaurant=restaurant,
        label=label,
        defaults={
            "branch": branch,
            "capacity": int(request.POST.get("capacity") or 4),
            "qr_token": token,
            "is_active": True,
        },
    )
    messages.success(request, "Table saved and QR token generated.")
    return redirect("table-qr")


@login_required
def table_qr_png(request, table_id):
    require_staff_role(request.user, ["owner", "manager"])
    restaurant = get_user_restaurant(request.user)
    table = get_object_or_404(RestaurantTable, pk=table_id, restaurant=restaurant)
    qr_url = request.build_absolute_uri(f"/public/{restaurant.slug}/menu/?table={table.qr_token}")
    image = qrcode.make(qr_url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


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
