from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from core.models import (
    Branch,
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


class Command(BaseCommand):
    help = "Seed a local demo restaurant for the RestBora prototype."

    def handle(self, *args, **options):
        restaurant, _ = Restaurant.objects.get_or_create(
            slug="bora-local-foods",
            defaults={
                "name": "Bora Local Foods",
                "phone": "+255 700 000 000",
                "location": "Dar es Salaam",
                "opening_hours": "07:00 - 22:00",
                "receipt_footer": "Asante sana. Karibu tena.",
            },
        )
        branch, _ = Branch.objects.get_or_create(restaurant=restaurant, name="Main Branch", defaults={"location": "Dar es Salaam"})

        staff = [
            ("owner", "owner", True),
            ("manager", "manager", False),
            ("waiter", "waiter", False),
            ("kitchen", "kitchen", False),
            ("cashier", "cashier", False),
        ]
        for username, role, is_superuser in staff:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password("password123")
                user.is_staff = True
                user.is_superuser = is_superuser
                user.save()
            StaffProfile.objects.get_or_create(user=user, restaurant=restaurant, defaults={"branch": branch, "role": role})

        categories = {
            "Breakfast": 1,
            "Lunch": 2,
            "Drinks": 3,
            "Snacks": 4,
        }
        category_objs = {}
        for name, sort_order in categories.items():
            category_objs[name], _ = MenuCategory.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={"sort_order": sort_order},
            )

        menu_items = [
            ("Chips Mayai", "Lunch", "Classic chips omelette", 4500, 2200, 12, True),
            ("Pilau Beef", "Lunch", "Spiced rice with beef", 7000, 3600, 20, True),
            ("Wali Maharage", "Lunch", "Rice and beans", 5000, 2100, 15, False),
            ("Chapati", "Breakfast", "Soft pan chapati", 1000, 400, 5, False),
            ("Mandazi", "Breakfast", "Fresh fried mandazi", 500, 150, 5, False),
            ("Soda", "Drinks", "Cold soda", 1500, 900, 1, True),
            ("Fresh Juice", "Drinks", "Seasonal fruit juice", 3000, 1400, 6, False),
            ("Samosa", "Snacks", "Beef samosa", 1000, 450, 5, False),
        ]
        for name, category, description, price, cost, minutes, popular in menu_items:
            MenuItem.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={
                    "category": category_objs[category],
                    "description": description,
                    "price": Decimal(price),
                    "estimated_food_cost": Decimal(cost),
                    "preparation_minutes": minutes,
                    "is_popular": popular,
                },
            )

        for label in ["T1", "T2", "T3", "T4", "Takeaway"]:
            RestaurantTable.objects.get_or_create(
                restaurant=restaurant,
                label=label,
                defaults={"branch": branch, "capacity": 4, "qr_token": slugify(f"{restaurant.slug}-{label}")},
            )

        stock_items = [
            ("Rice", "kg", 18, 10),
            ("Potatoes", "kg", 8, 10),
            ("Cooking oil", "ltr", 5, 4),
            ("Soda", "bottles", 48, 20),
            ("Gas", "kg", 3, 5),
            ("Packaging boxes", "pcs", 35, 25),
        ]
        for name, unit, qty, threshold in stock_items:
            InventoryItem.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={"unit": unit, "current_quantity": Decimal(qty), "low_stock_threshold": Decimal(threshold)},
            )

        Expense.objects.get_or_create(
            restaurant=restaurant,
            category=Expense.Category.CHARCOAL,
            amount=Decimal("15000"),
            note="Morning cooking fuel",
        )

        if not Order.objects.filter(restaurant=restaurant).exists():
            table = RestaurantTable.objects.filter(restaurant=restaurant, label="T1").first()
            chips = MenuItem.objects.get(restaurant=restaurant, name="Chips Mayai")
            soda = MenuItem.objects.get(restaurant=restaurant, name="Soda")
            order = Order.objects.create(restaurant=restaurant, branch=branch, table=table, customer_name="Demo Customer", status=Order.Status.SERVED)
            OrderItem.objects.create(order=order, menu_item=chips, item_name=chips.name, quantity=2, unit_price=chips.price, estimated_unit_food_cost=chips.estimated_food_cost)
            OrderItem.objects.create(order=order, menu_item=soda, item_name=soda.name, quantity=2, unit_price=soda.price, estimated_unit_food_cost=soda.estimated_food_cost)
            Payment.objects.create(order=order, method=Payment.Method.CASH, amount=order.subtotal)

        self.stdout.write(self.style.SUCCESS("Demo data ready. Users: owner/manager/waiter/kitchen/cashier, password: password123"))
