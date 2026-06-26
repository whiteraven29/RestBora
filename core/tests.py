from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils.text import slugify

from .models import Branch, MenuCategory, MenuItem, Order, Restaurant, RestaurantTable, StaffProfile


class PrototypeFlowTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")
        self.restaurant = Restaurant.objects.create(name="Test Foods", slug="test-foods", currency="TZS")
        self.branch = Branch.objects.create(restaurant=self.restaurant, name="Main Branch")
        self.owner = User.objects.create_user(username="owner", password="password123")
        StaffProfile.objects.create(
            user=self.owner,
            restaurant=self.restaurant,
            branch=self.branch,
            role=StaffProfile.Role.OWNER,
        )
        self.table = RestaurantTable.objects.create(
            restaurant=self.restaurant,
            branch=self.branch,
            label="T1",
            qr_token=slugify("test-foods-t1"),
        )
        self.category = MenuCategory.objects.create(restaurant=self.restaurant, name="Lunch")
        self.item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name="Pilau",
            price=Decimal("7000.00"),
            estimated_food_cost=Decimal("3500.00"),
        )

    def test_main_screens_render(self):
        self.client.login(username="owner", password="password123")
        paths = [
            "/",
            "/waiter/",
            "/kitchen/",
            "/cashier/",
            "/inventory/",
            "/menu/",
            "/tables/qr/",
            "/public/test-foods/menu/",
            "/api/public/restaurants/test-foods/menu/",
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_waiter_to_payment_flow(self):
        self.client.login(username="owner", password="password123")
        response = self.client.post(
            "/waiter/orders/",
            {
                "restaurant": self.restaurant.id,
                "table": self.table.id,
                "customer_name": "Jane",
                f"item_{self.item.id}": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(customer_name="Jane")
        self.assertEqual(order.subtotal, Decimal("14000.00"))

        for status, next_page in [("preparing", "kitchen"), ("ready", "kitchen"), ("served", "waiter")]:
            response = self.client.post(f"/orders/{order.id}/status/", {"status": status, "next": next_page})
            self.assertEqual(response.status_code, 302)

        response = self.client.post(
            f"/cashier/orders/{order.id}/payments/",
            {"method": "cash", "amount": "14000.00", "reference": "CASH"},
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.balance_due, Decimal("0.00"))

    def test_food_creation_and_table_qr_generation(self):
        self.client.login(username="owner", password="password123")

        response = self.client.post(
            "/menu/items/",
            {
                "category": self.category.id,
                "name": "Chips Mayai",
                "description": "Chips omelette",
                "price": "4500.00",
                "estimated_food_cost": "2000.00",
                "preparation_minutes": "12",
                "is_available": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MenuItem.objects.filter(restaurant=self.restaurant, name="Chips Mayai").exists())

        response = self.client.post("/tables/", {"label": "T2", "capacity": "4"})
        self.assertEqual(response.status_code, 302)
        table = RestaurantTable.objects.get(restaurant=self.restaurant, label="T2")

        response = self.client.get(f"/tables/{table.id}/qr.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
