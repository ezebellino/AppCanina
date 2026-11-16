from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse
from organizations.models import Organization, OrganizationMembership
from .models import Sale, SaleLine
from .receipts import receipt_data


class ReceiptTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("receipt-seller")
        self.user.user_permissions.add(Permission.objects.get(codename="add_sale"))
        self.org = Organization.objects.create(name="Veterinaria A", kind="veterinary")
        OrganizationMembership.objects.create(organization=self.org, user=self.user)
        self.sale = Sale.objects.create(organization=self.org, seller=self.user, total=Decimal("8500.50"), payment_method="transfer")
        SaleLine.objects.create(sale=self.sale, description="Alimento & cuidado <especial>", quantity=Decimal("0.5"), unit_price=Decimal("17001"), total=self.sale.total)
        self.url = reverse("sale_receipt", args=[self.sale.pk])
        self.client.force_login(self.user)

    def test_own_seller_can_share_exact_recorded_detail_without_view_permission(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "8.500,50")
        self.assertContains(response, "Alimento &amp; cuidado &lt;especial&gt;")
        self.assertIn("no-store", response["Cache-Control"])
        text = parse_qs(urlsplit(response.context["whatsapp_url"]).query)["text"][0]
        self.assertEqual(text, response.context["receipt"]["text"])
        self.assertIn("0,5 × $ 17.001,00 = $ 8.500,50", text)
        self.assertIn(f"V-{self.sale.pk:08d}", text)
        self.assertNotIn("/comprobante/", text)

    def test_add_permission_does_not_grant_access_to_other_seller(self):
        self.sale.seller = User.objects.create_user("other-seller")
        self.sale.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.user.user_permissions.add(Permission.objects.get(codename="view_sale"))
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_other_organization_and_revoked_membership_stay_private(self):
        self.user.user_permissions.add(Permission.objects.get(codename="view_sale"))
        other = Organization.objects.create(name="Other", kind="veterinary")
        self.sale.organization = other
        self.sale.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.sale.organization = self.org
        self.sale.save()
        self.org.memberships.all().delete()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_login_and_permission_required(self):
        self.user.user_permissions.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_long_receipt_keeps_all_lines_and_offers_copy(self):
        SaleLine.objects.bulk_create([SaleLine(sale=self.sale, description="Descripción larga " * 9, quantity=1, unit_price=0, total=0) for _ in range(40)])
        response = self.client.get(self.url)
        self.assertIsNone(response.context["whatsapp_url"])
        self.assertEqual(len(response.context["receipt"]["items"]), 41)
        self.assertContains(response, "Copiá el texto completo")

    def test_legacy_sale_preserves_total(self):
        self.sale.lines.all().delete()
        data = receipt_data(self.sale)
        self.assertEqual(data["total"], "8.500,50")
        self.assertEqual(data["items"][0]["description"], "Venta registrada")
