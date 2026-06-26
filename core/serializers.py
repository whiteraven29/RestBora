from decimal import Decimal

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
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


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = "__all__"


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"


class StaffProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = StaffProfile
        fields = ["id", "username", "full_name", "restaurant", "branch", "role", "phone", "is_active"]


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = "__all__"


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = MenuItem
        fields = "__all__"


class RestaurantTableSerializer(serializers.ModelSerializer):
    qr_url = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantTable
        fields = "__all__"

    def get_qr_url(self, table):
        request = self.context.get("request")
        path = f"/public/{table.restaurant.slug}/menu/?table={table.qr_token}"
        return request.build_absolute_uri(path) if request else path


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"


class OrderItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "menu_item", "item_name", "quantity", "unit_price", "line_total", "notes"]


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    table_label = serializers.CharField(source="table.label", read_only=True)
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"


class OrderItemWriteSerializer(serializers.Serializer):
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.filter(is_available=True))
    quantity = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "restaurant",
            "branch",
            "order_type",
            "table",
            "waiter",
            "customer_name",
            "customer_phone",
            "notes",
            "items",
        ]

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        restaurant = validated_data["restaurant"]
        phone = validated_data.get("customer_phone", "").strip()
        name = validated_data.get("customer_name", "").strip() or "Guest"
        customer = None
        if phone:
            customer, _ = Customer.objects.get_or_create(
                restaurant=restaurant,
                phone=phone,
                defaults={"name": name},
            )
            customer.name = name
            customer.last_order_at = timezone.now()
            customer.save(update_fields=["name", "last_order_at", "updated_at"])
            validated_data["customer"] = customer

        order = Order.objects.create(**validated_data)
        for item in items:
            menu_item = item["menu_item"]
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                item_name=menu_item.name,
                quantity=item["quantity"],
                unit_price=menu_item.price,
                estimated_unit_food_cost=menu_item.estimated_food_cost,
                notes=item.get("notes", ""),
            )

        if customer:
            customer.total_orders += 1
            customer.total_spending += order.subtotal
            customer.last_order_at = timezone.now()
            customer.save(update_fields=["total_orders", "total_spending", "last_order_at", "updated_at"])
            LoyaltyTransaction.objects.create(customer=customer, points=1, reason="Completed order placeholder", order=order)
        return order


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"

    def validate(self, attrs):
        if attrs["amount"] <= Decimal("0.00"):
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return attrs


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = "__all__"


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = "__all__"


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    restaurant_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )
        restaurant = Restaurant.objects.create(
            name=validated_data["restaurant_name"],
            phone=validated_data.get("phone", ""),
            receipt_footer="Thank you for eating with us.",
        )
        branch = Branch.objects.create(restaurant=restaurant)
        StaffProfile.objects.create(user=user, restaurant=restaurant, branch=branch, role=StaffProfile.Role.OWNER)
        return user
