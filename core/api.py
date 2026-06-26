from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import (
    Customer,
    Expense,
    InventoryItem,
    MenuCategory,
    MenuItem,
    Order,
    Payment,
    Restaurant,
    RestaurantTable,
    StaffProfile,
    StockMovement,
)
from .serializers import (
    CustomerSerializer,
    ExpenseSerializer,
    InventoryItemSerializer,
    MenuCategorySerializer,
    MenuItemSerializer,
    OrderCreateSerializer,
    OrderReadSerializer,
    PaymentSerializer,
    RestaurantSerializer,
    RestaurantTableSerializer,
    StaffProfileSerializer,
    StockMovementSerializer,
    UserRegisterSerializer,
)


def first_restaurant():
    return Restaurant.objects.first()


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = UserRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return Response({"id": user.id, "username": user.username}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
    if not user:
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response({"detail": "Logged in."})


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        restaurant = first_restaurant()
        return Response(self.get_serializer(restaurant).data if restaurant else {})


class StaffViewSet(viewsets.ModelViewSet):
    queryset = StaffProfile.objects.select_related("user", "restaurant", "branch")
    serializer_class = StaffProfileSerializer


class MenuCategoryViewSet(viewsets.ModelViewSet):
    queryset = MenuCategory.objects.select_related("restaurant")
    serializer_class = MenuCategorySerializer


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related("restaurant", "category")
    serializer_class = MenuItemSerializer
    filterset_fields = ["category", "is_available", "is_popular"]

    @action(detail=True, methods=["patch"])
    def availability(self, request, pk=None):
        item = self.get_object()
        item.is_available = bool(request.data.get("is_available", not item.is_available))
        item.save(update_fields=["is_available", "updated_at"])
        return Response(self.get_serializer(item).data)


class TableViewSet(viewsets.ModelViewSet):
    queryset = RestaurantTable.objects.select_related("restaurant", "branch")
    serializer_class = RestaurantTableSerializer

    @action(detail=True, methods=["get"])
    def qr(self, request, pk=None):
        table = self.get_object()
        return Response(RestaurantTableSerializer(table, context={"request": request}).data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related("items").select_related("restaurant", "table", "customer", "waiter")

    def get_serializer_class(self):
        return OrderCreateSerializer if self.action == "create" else OrderReadSerializer

    @action(detail=False, methods=["get"])
    def kitchen(self, request):
        orders = self.get_queryset().filter(status__in=[Order.Status.PENDING, Order.Status.ACCEPTED, Order.Status.PREPARING])
        return Response(OrderReadSerializer(orders, many=True).data)

    @action(detail=False, methods=["get"])
    def unpaid(self, request):
        orders = self.get_queryset().exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED])
        orders = [order for order in orders if order.balance_due > 0]
        return Response(OrderReadSerializer(orders, many=True).data)

    @action(detail=True, methods=["patch"])
    def status(self, request, pk=None):
        order = self.get_object()
        order.status = request.data["status"]
        order.save(update_fields=["status", "updated_at"])
        return Response(OrderReadSerializer(order).data)

    @action(detail=True, methods=["patch"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order.status = Order.Status.CANCELLED
        order.cancellation_reason = request.data.get("reason", "")
        order.save(update_fields=["status", "cancellation_reason", "updated_at"])
        return Response(OrderReadSerializer(order).data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order", "received_by")
    serializer_class = PaymentSerializer

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request):
        today = timezone.localdate()
        rows = (
            self.get_queryset()
            .filter(paid_at__date=today)
            .values("method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("method")
        )
        return Response(list(rows))


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related("restaurant")
    serializer_class = InventoryItemSerializer

    @action(detail=True, methods=["post"])
    def movement(self, request, pk=None):
        item = self.get_object()
        serializer = StockMovementSerializer(data={**request.data, "item": item.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        items = [item for item in self.get_queryset() if item.is_low_stock]
        return Response(self.get_serializer(items, many=True).data)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.select_related("restaurant")
    serializer_class = ExpenseSerializer
    filterset_fields = ["category", "expense_date"]


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.select_related("restaurant")
    serializer_class = CustomerSerializer

    @action(detail=False, methods=["get"])
    def top(self, request):
        customers = self.get_queryset().order_by("-total_spending", "-total_orders")[:10]
        return Response(self.get_serializer(customers, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_menu(request, slug):
    restaurant = Restaurant.objects.get(slug=slug)
    categories = MenuCategory.objects.filter(restaurant=restaurant, is_active=True).prefetch_related("items")
    return Response(
        {
            "restaurant": RestaurantSerializer(restaurant).data,
            "categories": MenuCategorySerializer(categories, many=True).data,
            "items": MenuItemSerializer(MenuItem.objects.filter(restaurant=restaurant, is_available=True), many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def public_order(request, slug):
    restaurant = Restaurant.objects.get(slug=slug)
    table = None
    if request.data.get("table_token"):
        table = RestaurantTable.objects.filter(restaurant=restaurant, qr_token=request.data["table_token"]).first()
    serializer = OrderCreateSerializer(
        data={
            **request.data,
            "restaurant": restaurant.id,
            "table": table.id if table else None,
            "order_type": Order.OrderType.QR_TABLE if table else Order.OrderType.TAKEAWAY,
        }
    )
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    return Response(OrderReadSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def public_order_status(request, order_number):
    order = Order.objects.get(order_number=order_number)
    return Response({"order_number": order.order_number, "status": order.status})


@api_view(["GET"])
def dashboard_report(request):
    restaurant = first_restaurant()
    today = timezone.localdate()
    today_orders = Order.objects.filter(restaurant=restaurant, created_at__date=today) if restaurant else Order.objects.none()
    today_expenses = Expense.objects.filter(restaurant=restaurant, expense_date=today) if restaurant else Expense.objects.none()
    sales = today_orders.filter(status=Order.Status.PAID).aggregate(total=Sum("subtotal"))["total"] or 0
    expenses = today_expenses.aggregate(total=Sum("amount"))["total"] or 0
    food_cost = today_orders.filter(status=Order.Status.PAID).aggregate(total=Sum("estimated_food_cost_total"))["total"] or 0
    return Response(
        {
            "today_sales": sales,
            "total_orders": today_orders.count(),
            "paid_orders": today_orders.filter(status=Order.Status.PAID).count(),
            "unpaid_orders": today_orders.exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED]).count(),
            "cancelled_orders": today_orders.filter(status=Order.Status.CANCELLED).count(),
            "today_expenses": expenses,
            "estimated_profit_loss": sales - expenses - food_cost,
            "low_stock_alerts": InventoryItem.objects.filter(restaurant=restaurant).count() if restaurant else 0,
            "period": str(today),
        }
    )


@api_view(["GET"])
def profit_loss_report(request):
    days = int(request.GET.get("days", 30))
    since = timezone.localdate() - timedelta(days=days)
    restaurant = first_restaurant()
    orders = Order.objects.filter(restaurant=restaurant, created_at__date__gte=since, status=Order.Status.PAID)
    expenses = Expense.objects.filter(restaurant=restaurant, expense_date__gte=since)
    sales = orders.aggregate(total=Sum("subtotal"))["total"] or 0
    costs = orders.aggregate(total=Sum("estimated_food_cost_total"))["total"] or 0
    expense_total = expenses.aggregate(total=Sum("amount"))["total"] or 0
    return Response({"sales": sales, "estimated_food_costs": costs, "expenses": expense_total, "estimated_profit": sales - costs - expense_total})
