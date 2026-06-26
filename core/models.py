from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Restaurant(TimeStampedModel):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True)
    phone = models.CharField(max_length=40, blank=True)
    location = models.CharField(max_length=255, blank=True)
    opening_hours = models.CharField(max_length=120, blank=True)
    service_options = models.CharField(max_length=255, default="dine-in,takeaway,delivery-request")
    receipt_footer = models.CharField(max_length=255, blank=True)
    currency = models.CharField(max_length=8, default="TZS")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Branch(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=120, default="Main Branch")
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"


class StaffProfile(TimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        MANAGER = "manager", "Manager"
        WAITER = "waiter", "Waiter"
        KITCHEN = "kitchen", "Kitchen"
        CASHIER = "cashier", "Cashier"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="staff")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class RestaurantTable(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="tables")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    label = models.CharField(max_length=40)
    capacity = models.PositiveIntegerField(default=4)
    qr_token = models.SlugField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("restaurant", "label")
        ordering = ["label"]

    def __str__(self):
        return self.label


class MenuCategory(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_categories")
    name = models.CharField(max_length=120)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        unique_together = ("restaurant", "name")

    def __str__(self):
        return self.name


class MenuItem(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="menu_items")
    category = models.ForeignKey(MenuCategory, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="menu/", blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_food_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    preparation_minutes = models.PositiveIntegerField(default=15)
    is_available = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)

    class Meta:
        ordering = ["category__sort_order", "name"]
        unique_together = ("restaurant", "name")

    def __str__(self):
        return self.name


class Customer(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    total_orders = models.PositiveIntegerField(default=0)
    total_spending = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    loyalty_points = models.IntegerField(default=0)
    last_order_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("restaurant", "phone")
        ordering = ["-last_order_at", "name"]

    def __str__(self):
        return f"{self.name} - {self.phone}"


class Order(TimeStampedModel):
    class OrderType(models.TextChoices):
        DINE_IN = "dine_in", "Dine-in"
        TAKEAWAY = "takeaway", "Takeaway"
        QR_TABLE = "qr_table", "QR Table"
        DELIVERY_REQUEST = "delivery_request", "Delivery Request"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"
        SERVED = "served", "Served"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="orders")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    order_number = models.CharField(max_length=32, unique=True, blank=True)
    order_type = models.CharField(max_length=30, choices=OrderType.choices, default=OrderType.DINE_IN)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    table = models.ForeignKey(RestaurantTable, on_delete=models.SET_NULL, null=True, blank=True)
    waiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="waiter_orders")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    customer_name = models.CharField(max_length=120, blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    estimated_food_cost_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_paid = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            timestamp = timezone.now().strftime("%y%m%d%H%M%S")
            suffix = Order.objects.count() + 1
            self.order_number = f"RB{timestamp}{suffix:04d}"
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return max(self.subtotal - self.total_paid, Decimal("0.00"))

    def refresh_totals(self):
        totals = self.items.aggregate(
            subtotal=models.Sum(models.F("line_total")),
            cost=models.Sum(models.F("estimated_food_cost_total")),
        )
        self.subtotal = totals["subtotal"] or Decimal("0.00")
        self.estimated_food_cost_total = totals["cost"] or Decimal("0.00")
        self.save(update_fields=["subtotal", "estimated_food_cost_total", "updated_at"])

    def __str__(self):
        return self.order_number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    item_name = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_unit_food_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    estimated_food_cost_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    notes = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if self.menu_item_id:
            self.item_name = self.item_name or self.menu_item.name
            self.unit_price = self.unit_price or self.menu_item.price
            self.estimated_unit_food_cost = self.estimated_unit_food_cost or self.menu_item.estimated_food_cost
        self.line_total = self.unit_price * self.quantity
        self.estimated_food_cost_total = self.estimated_unit_food_cost * self.quantity
        super().save(*args, **kwargs)
        self.order.refresh_totals()

    def __str__(self):
        return f"{self.quantity} x {self.item_name}"


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        MPESA = "mpesa", "M-Pesa"
        AIRTEL_MONEY = "airtel_money", "Airtel Money"
        TIGO_PESA = "tigo_pesa", "Tigo Pesa"
        HALOPESA = "halopesa", "HaloPesa"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        CARD = "card", "Card"
        PAY_LATER = "pay_later", "Pay later"

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments")
    method = models.CharField(max_length=30, choices=Method.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=120, blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total_paid = self.order.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        self.order.total_paid = total_paid
        if total_paid >= self.order.subtotal and self.order.status != Order.Status.CANCELLED:
            self.order.status = Order.Status.PAID
        self.order.save(update_fields=["total_paid", "status", "updated_at"])

    def __str__(self):
        return f"{self.order.order_number} - {self.amount}"


class InventoryItem(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="inventory_items")
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=30, default="pcs")
    current_quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    low_stock_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("restaurant", "name")
        ordering = ["name"]

    @property
    def is_low_stock(self):
        return self.current_quantity <= self.low_stock_threshold

    def __str__(self):
        return self.name


class StockMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        USAGE = "usage", "Usage"
        SPOILAGE = "spoilage", "Spoilage"
        ADJUSTMENT = "adjustment", "Adjustment"

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    note = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.movement_type == self.MovementType.PURCHASE:
            self.item.current_quantity += self.quantity
        elif self.movement_type in [self.MovementType.USAGE, self.MovementType.SPOILAGE]:
            self.item.current_quantity -= self.quantity
        else:
            self.item.current_quantity = self.quantity
        self.item.save(update_fields=["current_quantity", "updated_at"])

    def __str__(self):
        return f"{self.item.name} {self.movement_type} {self.quantity}"


class Expense(TimeStampedModel):
    class Category(models.TextChoices):
        FOOD_STOCK = "food_stock", "Food stock purchase"
        STAFF_WAGES = "staff_wages", "Staff wages"
        RENT = "rent", "Rent"
        ELECTRICITY = "electricity", "Electricity"
        WATER = "water", "Water"
        GAS = "gas", "Gas"
        CHARCOAL = "charcoal", "Charcoal"
        TRANSPORT = "transport", "Transport"
        REPAIRS = "repairs", "Repairs"
        INTERNET = "internet", "Internet"
        CLEANING = "cleaning", "Cleaning"
        PACKAGING = "packaging", "Packaging"
        OTHER = "other", "Other"

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=30, choices=Category.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    expense_date = models.DateField(default=timezone.localdate)
    note = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} - {self.amount}"


class LoyaltyTransaction(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="loyalty_transactions")
    points = models.IntegerField()
    reason = models.CharField(max_length=255)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.customer.loyalty_points += self.points
            self.customer.save(update_fields=["loyalty_points", "updated_at"])

    def __str__(self):
        return f"{self.customer.phone}: {self.points}"


class AuditLog(TimeStampedModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.action
