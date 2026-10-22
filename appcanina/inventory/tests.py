from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from .models import Brand, Product, Supplier
from organizations.models import Organization, OrganizationMembership


class InventoryAlertsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("inventory-user", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="view_product"))
        self.organization = Organization.objects.create(name="Veterinaria Inventario", kind="veterinary", is_business_profile=True)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.brand = Brand.objects.create(name="Marca alerta", organization=self.organization)
        self.supplier = Supplier.objects.create(name="Proveedor alerta", organization=self.organization)
        self.client.force_login(self.user)

    def create_product(self, name, **kwargs):
        defaults = {"organization": self.organization, "category": "medicine", "brand": self.brand, "supplier": self.supplier, "price": Decimal("1000"), "stock": Decimal("10"), "minimum_stock": Decimal("2")}
        defaults.update(kwargs)
        return Product.objects.create(name=name, **defaults)

    def test_alerts_group_low_stock_expired_and_expiring_products(self):
        today = timezone.localdate()
        low_stock = self.create_product("Pipeta con poco stock", stock=Decimal("2"))
        expired = self.create_product("Medicamento vencido", expires_on=today - timedelta(days=1))
        expiring = self.create_product("Shampoo próximo a vencer", expires_on=today + timedelta(days=10))
        self.create_product("Alimento sin alerta", expires_on=today + timedelta(days=60))
        response = self.client.get(reverse("inventory_alerts"))
        self.assertContains(response, low_stock.name)
        self.assertContains(response, expired.name)
        self.assertContains(response, expiring.name)
        self.assertNotContains(response, "Alimento sin alerta")

    def test_inventory_can_filter_products_by_supplier(self):
        other_supplier = Supplier.objects.create(name="Otro proveedor", organization=self.organization)
        self.create_product("Alimento del proveedor")
        self.create_product("Alimento ajeno", supplier=other_supplier)

        response = self.client.get(reverse("inventory_list"), {"supplier": self.supplier.id})

        self.assertContains(response, "Alimento del proveedor")
        self.assertNotContains(response, "Alimento ajeno")

    def test_inventory_does_not_show_products_from_another_organization(self):
        other_organization = Organization.objects.create(name="Veterinaria ajena", kind="veterinary")
        other_brand = Brand.objects.create(name="Marca ajena", organization=other_organization)
        other_supplier = Supplier.objects.create(name="Proveedor ajeno", organization=other_organization)
        Product.objects.create(organization=other_organization, name="Producto oculto", category="food", brand=other_brand, supplier=other_supplier, price=Decimal("500"))
        self.create_product("Producto propio")

        response = self.client.get(reverse("inventory_list"))

        self.assertContains(response, "Producto propio")
        self.assertNotContains(response, "Producto oculto")


class ProductImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("importer", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="add_product"), Permission.objects.get(codename="view_product"))
        self.organization = Organization.objects.create(name="Veterinaria Importadora", kind="veterinary", is_business_profile=True)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.client.force_login(self.user)

    def workbook_file(self, rows):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["Código interno", "Nombre", "Categoría", "Marca", "Proveedor", "Precio", "Stock", "Stock mínimo", "Vencimiento", "Requiere receta"])
        for row in rows:
            worksheet.append(row)
        stream = BytesIO()
        workbook.save(stream)
        return SimpleUploadedFile("productos.xlsx", stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_preview_then_confirm_creates_products_and_related_entities(self):
        upload = self.workbook_file([["MED-001", "Antiparasitario", "Pipeta", "Marca Salud", "Distribuidor", "12500,50", 8, 2, "2030-12-31", "Sí"]])
        response = self.client.post(reverse("product_import"), {"action": "preview", "file": upload})
        self.assertContains(response, "1 productos listos para importar")
        response = self.client.post(reverse("product_import"), {"action": "confirm"})
        self.assertRedirects(response, reverse("inventory_list"))
        product = Product.objects.get(sku="MED-001")
        self.assertEqual(product.category, "antiparasitic")
        self.assertEqual(product.price, Decimal("12500.50"))
        self.assertTrue(product.requires_prescription)
        self.assertEqual(product.brand.name, "Marca Salud")

    def test_existing_sku_is_updated_and_invalid_row_is_not_imported(self):
        brand = Brand.objects.create(name="Marca previa", organization=self.organization)
        supplier = Supplier.objects.create(name="Proveedor previo", organization=self.organization)
        product = Product.objects.create(organization=self.organization, sku="SKU-1", name="Producto previo", category="food", brand=brand, supplier=supplier, price=Decimal("100"))
        upload = self.workbook_file([["SKU-1", "Producto actualizado", "Alimento", "Marca previa", "Proveedor previo", "250", 3, 1, "", "No"]])
        self.client.post(reverse("product_import"), {"action": "preview", "file": upload})
        self.client.post(reverse("product_import"), {"action": "confirm"})
        self.assertEqual(Product.objects.count(), 1)
        product.refresh_from_db()
        self.assertEqual(product.name, "Producto actualizado")
        self.assertEqual(product.price, Decimal("250"))
        invalid_upload = self.workbook_file([["BAD-1", "Inválido", "Categoría rara", "Marca", "Proveedor", "100", 1, 0, "", "No"]])
        response = self.client.post(reverse("product_import"), {"action": "preview", "file": invalid_upload})
        self.assertContains(response, "Categoría no es válido")
        self.assertFalse(Product.objects.filter(sku="BAD-1").exists())


class ProductCommercialNameTests(TestCase):
    def test_commercial_name_is_preferred_as_the_product_display_name(self):
        brand = Brand.objects.create(name="Marca profesional")
        supplier = Supplier.objects.create(name="Proveedor profesional")
        product = Product.objects.create(name="Alimento adulto 15 kg", commercial_name="Vitalcan Complete Adultos 15 kg", category="food", brand=brand, supplier=supplier, price=Decimal("12000"))
        self.assertEqual(product.display_name, "Vitalcan Complete Adultos 15 kg")
        self.assertEqual(str(product), "Vitalcan Complete Adultos 15 kg")


class BusinessProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("business-owner", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="add_organization"))
        self.client.force_login(self.user)

    def test_owner_can_create_the_single_business_profile(self):
        response = self.client.post(reverse("business_profile"), {"name": "Veterinaria Patitas", "kind": "veterinary", "phone": "11 5555 1234", "email": "hola@patitas.test", "address": "Av. Siempre Viva 123"})
        self.assertRedirects(response, reverse("business_profile"))
        profile = Organization.objects.get(is_business_profile=True)
        self.assertEqual(profile.name, "Veterinaria Patitas")
        self.assertEqual(profile.phone, "11 5555 1234")

    def test_shelter_manager_edits_own_profile_without_commerce_links(self):
        shelter = Organization.objects.create(name="Refugio Patitas", kind="shelter", donation_alias="patitas.demo")
        from organizations.models import OrganizationMembership
        OrganizationMembership.objects.create(organization=shelter, user=self.user)

        response = self.client.get(reverse("business_profile"))

        self.assertContains(response, "Refugio Patitas")
        self.assertContains(response, "patitas.demo")
        self.assertNotContains(response, "Gestionar marcas")
        self.assertNotContains(response, "Ver proveedores")

        response = self.client.post(reverse("business_profile"), {"name": "Refugio Patitas Unido", "kind": "shelter", "phone": "11 5555 0000", "email": "hola@patitas.test", "address": "Calle 12", "donation_alias": "patitas.unido", "donation_message": "Cada aporte suma."})
        self.assertRedirects(response, reverse("business_profile"))
        shelter.refresh_from_db()
        self.assertEqual(shelter.name, "Refugio Patitas Unido")
        self.assertEqual(shelter.donation_alias, "patitas.unido")
