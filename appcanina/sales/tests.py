from decimal import Decimal
from datetime import datetime

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from grooming.models import GroomingAppointment, GroomingService
from inventory.models import Brand, Product, Supplier
from patients.models import Contact, Patient, PatientContact
from organizations.models import Organization, OrganizationMembership
from .models import CashMovement, CashSession, Sale, SaleLine
from .views import _cash_summary, _closed_cash_history


class MixedSaleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("seller", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="add_sale"))
        self.organization = Organization.objects.create(name="Veterinaria Ventas", kind="veterinary", is_business_profile=True)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.brand = Brand.objects.create(name="Marca prueba", organization=self.organization)
        self.supplier = Supplier.objects.create(name="Proveedor prueba", organization=self.organization)
        self.product = Product.objects.create(organization=self.organization, name="Alimento", category="food", brand=self.brand, supplier=self.supplier, sale_unit="kg", price=Decimal("10000"), stock=Decimal("5"))
        self.service = GroomingService.objects.create(name="Baño", duration_minutes=30)
        CashSession.objects.create(organization=self.organization, opened_by=self.user, opening_amount=Decimal("0"))
        self.client.force_login(self.user)

    def test_checkout_mixed_cart_creates_lines_and_reduces_product_stock(self):
        session = self.client.session
        session["sale_cart"] = [{"kind":"product","id":self.product.id,"description":"Alimento","quantity":"0.5","unit_price":"10000","total":"5000"},{"kind":"service","id":self.service.id,"description":"Baño","quantity":"1","unit_price":"7000","total":"7000"}]
        session.save()
        response = self.client.post(reverse("sale_create"), {"action":"checkout", "patient":"", "payment_method":"cash", "payment_reference":""})
        self.assertRedirects(response, reverse("sale_create"))
        sale = Sale.objects.get()
        self.assertEqual(sale.total, Decimal("12000"))
        self.assertEqual(SaleLine.objects.filter(sale=sale).count(), 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, Decimal("4.5"))

    def test_sale_page_includes_quick_product_search_and_filter_data(self):
        response = self.client.get(reverse("sale_create"))
        self.assertContains(response, "Buscar producto")
        self.assertContains(response, "sale-category-filter")
        self.assertContains(response, 'data-category="food"')


class AppointmentCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("groomer-seller", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="add_sale"), Permission.objects.get(codename="view_groomingappointment"))
        self.organization = Organization.objects.create(name="Veterinaria Peluquería", kind="veterinary", is_business_profile=True)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.patient = Patient.objects.create(name="Mora", species="dog", organization=self.organization)
        self.contact = Contact.objects.create(full_name="Ana responsable")
        PatientContact.objects.create(patient=self.patient, contact=self.contact, role="responsible", is_primary=True)
        self.service = GroomingService.objects.create(name="Baño", duration_minutes=45, price=Decimal("8500"))
        self.appointment = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.make_aware(datetime(2026, 7, 30, 10, 0)), status="done")
        self.client.force_login(self.user)

    def test_finalized_appointment_preloads_and_links_sale(self):
        response = self.client.get(reverse("sale_create_from_appointment", args=[self.appointment.id]))
        self.assertRedirects(response, reverse("sale_create"))
        response = self.client.post(reverse("sale_create"), {"action": "checkout", "patient": "", "payment_method": "transfer", "payment_reference": ""})
        self.assertRedirects(response, reverse("sale_create"))
        sale = Sale.objects.get()
        self.assertEqual(sale.grooming_appointment, self.appointment)
        self.assertEqual(sale.patient, self.patient)
        self.assertEqual(sale.contact, self.contact)
        self.assertEqual(sale.total, Decimal("8500"))


class CashSummaryTests(TestCase):
    def test_summary_separates_payment_methods_and_history_keeps_difference(self):
        user = User.objects.create_user("cashier", password="secret")
        session = CashSession.objects.create(opened_by=user, opening_amount=Decimal("1000"))
        Sale.objects.create(total=Decimal("2000"), payment_method="cash", seller=user, cash_session=session)
        Sale.objects.create(total=Decimal("3000"), payment_method="transfer", seller=user, cash_session=session)
        Sale.objects.create(total=Decimal("4000"), payment_method="qr", seller=user, cash_session=session)
        CashMovement.objects.create(session=session, kind="income", amount=Decimal("500"), note="Ajuste")
        CashMovement.objects.create(session=session, kind="withdrawal", amount=Decimal("200"), note="Retiro")
        summary = _cash_summary(session)
        self.assertEqual(summary["cash_sales"], Decimal("2000"))
        self.assertEqual(summary["transfer_sales"], Decimal("3000"))
        self.assertEqual(summary["qr_sales"], Decimal("4000"))
        self.assertEqual(summary["expected"], Decimal("3300"))
        session.closing_amount = Decimal("3200")
        session.closed_at = timezone.now()
        session.save()
        history = _closed_cash_history()
        self.assertEqual(history[0]["difference"], Decimal("-100"))


class DailyReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("report-user", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="view_sale"))
        self.organization = Organization.objects.create(name="Veterinaria Reportes", kind="veterinary", is_business_profile=True)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.client.force_login(self.user)

    def test_daily_report_groups_payment_methods_and_sale_lines(self):
        sale = Sale.objects.create(organization=self.organization, total=Decimal("5200"), payment_method="cash", seller=self.user)
        Sale.objects.create(organization=self.organization, total=Decimal("1800"), payment_method="transfer", seller=self.user)
        SaleLine.objects.create(sale=sale, description="Alimento balanceado", quantity=Decimal("2"), unit_price=Decimal("2600"), total=Decimal("5200"))
        response = self.client.get(reverse("daily_report"))
        self.assertContains(response, "Resumen del día")
        self.assertContains(response, "$7000")
        self.assertContains(response, "Alimento balanceado")

    def test_sales_history_excludes_other_organization_sales(self):
        other_organization = Organization.objects.create(name="Veterinaria ajena ventas", kind="veterinary")
        own_sale = Sale.objects.create(organization=self.organization, total=Decimal("1000"), payment_method="cash", seller=self.user)
        foreign_sale = Sale.objects.create(organization=other_organization, total=Decimal("9000"), payment_method="cash", seller=self.user)
        SaleLine.objects.create(sale=own_sale, description="Venta propia", quantity=Decimal("1"), unit_price=Decimal("1000"), total=Decimal("1000"))
        SaleLine.objects.create(sale=foreign_sale, description="Venta ajena", quantity=Decimal("1"), unit_price=Decimal("9000"), total=Decimal("9000"))

        response = self.client.get(reverse("sale_list"))

        self.assertContains(response, "Venta propia")
        self.assertNotContains(response, "Venta ajena")
