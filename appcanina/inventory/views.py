from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from organizations.forms import BusinessProfileForm
from organizations.models import Organization

from .forms import BrandForm, PriceIncreaseForm, ProductForm, ProductImportForm, SupplierForm
from .imports import parse_product_workbook
from .models import Brand, Product, Supplier


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def product_list(request):
    query = request.GET.get("q", "").strip()
    supplier_id = request.GET.get("supplier", "").strip()
    selected_supplier = None
    products = Product.objects.select_related("brand", "supplier").filter(active=True)
    if supplier_id:
        selected_supplier = get_object_or_404(Supplier, pk=supplier_id, active=True)
        products = products.filter(supplier=selected_supplier)
    if query:
        products = products.filter(Q(name__icontains=query) | Q(commercial_name__icontains=query) | Q(sku__icontains=query) | Q(brand__name__icontains=query) | Q(category__icontains=query) | Q(supplier__name__icontains=query))
    alert_count = Product.objects.filter(active=True).filter(Q(stock__lte=F("minimum_stock")) | Q(expires_on__lte=timezone.localdate() + timedelta(days=30))).count()
    return render(request, "inventory/product_list.html", {"products": products, "query": query, "selected_supplier": selected_supplier, "alert_count": alert_count})


@login_required
@permission_required("inventory.view_product", raise_exception=True)
def inventory_alerts(request):
    today = timezone.localdate()
    products = Product.objects.select_related("brand", "supplier").filter(active=True)
    low_stock = products.filter(stock__lte=F("minimum_stock"))
    expired = products.filter(expires_on__lt=today)
    expiring_soon = products.filter(expires_on__gte=today, expires_on__lte=today + timedelta(days=30))
    return render(request, "inventory/alerts.html", {"low_stock": low_stock, "expired": expired, "expiring_soon": expiring_soon, "today": today})


@login_required
@permission_required("inventory.add_product", raise_exception=True)
def product_create(request):
    if request.method == "POST" and "add_brand" in request.POST:
        brand_name = request.POST.get("new_brand", "").strip()
        if brand_name:
            brand, _ = Brand.objects.get_or_create(name__iexact=brand_name, defaults={"name": brand_name})
            messages.success(request, f"La marca {brand.name} ya está cargada y fue seleccionada.")
            return redirect(f"{request.path}?brand={brand.id}")
        messages.error(request, "Escribí el nombre de la marca antes de agregarla.")
        return redirect(request.path)
    form = ProductForm(request.POST or None, initial={"brand": request.GET.get("brand")})
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Producto creado y agregado al inventario.")
        return redirect("inventory_list")
    return render(request, "inventory/product_form.html", {"form": form})


def _import_row_for_session(row):
    serialized = {}
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            serialized[key] = value.isoformat()
        elif value is not None:
            serialized[key] = str(value)
        else:
            serialized[key] = None
    return serialized


def _import_row_from_session(row):
    from datetime import date
    from decimal import Decimal
    result = dict(row)
    for field in ("package_weight_kg", "price", "promotional_price", "stock", "minimum_stock"):
        if result[field] is not None:
            result[field] = Decimal(result[field])
    for field in ("promotion_starts_on", "promotion_ends_on", "expires_on"):
        if result[field]:
            result[field] = date.fromisoformat(result[field])
    return result


@login_required
@permission_required("inventory.add_product", raise_exception=True)
def product_import(request):
    preview_rows = request.session.get("inventory_import_preview", [])
    errors = []
    form = ProductImportForm()
    if request.method == "POST" and request.POST.get("action") == "preview":
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            rows, errors = parse_product_workbook(form.cleaned_data["file"])
            if not errors and not rows:
                errors = [{"line": 2, "message": "El archivo no contiene productos."}]
            if not errors:
                request.session["inventory_import_preview"] = [_import_row_for_session(row) for row in rows]
                request.session.modified = True
                preview_rows = request.session["inventory_import_preview"]
    elif request.method == "POST" and request.POST.get("action") == "confirm":
        if not preview_rows:
            messages.error(request, "Primero subí un archivo y revisá la vista previa.")
            return redirect("product_import")
        created = updated = 0
        with transaction.atomic():
            for serialized in preview_rows:
                row = _import_row_from_session(serialized)
                brand = Brand.objects.filter(name__iexact=row.pop("brand")).first()
                if not brand:
                    brand = Brand.objects.create(name=serialized["brand"])
                supplier = Supplier.objects.filter(name__iexact=row.pop("supplier")).first()
                if not supplier:
                    supplier = Supplier.objects.create(name=serialized["supplier"])
                sku = row["sku"]
                product = Product.objects.filter(sku=sku).first() if sku else None
                if product:
                    updated += 1
                else:
                    product = Product()
                    created += 1
                for field, value in row.items():
                    setattr(product, field, value)
                product.brand = brand
                product.supplier = supplier
                product.active = True
                product.full_clean()
                product.save()
        request.session.pop("inventory_import_preview", None)
        messages.success(request, f"Importación completada: {created} productos nuevos y {updated} actualizados.")
        return redirect("inventory_list")
    return render(request, "inventory/product_import.html", {"form": form, "preview_rows": preview_rows, "errors": errors})


@login_required
@permission_required("inventory.change_product", raise_exception=True)
def product_edit(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("inventory_list")
    return render(request, "inventory/product_form.html", {"form": form, "product": product})


@login_required
@permission_required("inventory.view_supplier", raise_exception=True)
def supplier_list(request):
    suppliers = Supplier.objects.filter(active=True).annotate(product_count=Count("products"))
    return render(request, "inventory/supplier_list.html", {"suppliers": suppliers})


@login_required
@permission_required("inventory.add_supplier", raise_exception=True)
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("supplier_list")
    return render(request, "inventory/simple_form.html", {"form": form, "title": "Nuevo proveedor", "back_url": "supplier_list"})


@login_required
@permission_required("inventory.change_product", raise_exception=True)
def supplier_price_increase(request, supplier_id):
    supplier = get_object_or_404(Supplier, pk=supplier_id, active=True)
    form = PriceIncreaseForm(request.POST or None)
    products = supplier.products.filter(active=True)
    if request.method == "POST" and form.is_valid():
        multiplier = 1 + form.cleaned_data["percentage"] / 100
        products.update(price=Round(F("price") * multiplier, 2))
        return redirect("supplier_list")
    return render(request, "inventory/price_increase_form.html", {"supplier": supplier, "form": form, "product_count": products.count()})


@login_required
@permission_required("inventory.view_brand", raise_exception=True)
def brand_list(request):
    return render(request, "inventory/brand_list.html", {"brands": Brand.objects.filter(active=True)})


@login_required
@permission_required("inventory.add_brand", raise_exception=True)
def brand_create(request):
    form = BrandForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("brand_list")
    return render(request, "inventory/simple_form.html", {"form": form, "title": "Nueva marca", "back_url": "brand_list"})


@login_required
@permission_required("auth.add_user", raise_exception=True)
def business_profile(request):
    profile = Organization.objects.filter(is_business_profile=True).first()
    form = BusinessProfileForm(request.POST or None, request.FILES or None, instance=profile)
    can_edit = request.user.has_perm("organizations.change_organization") or request.user.has_perm("organizations.add_organization")
    if request.method == "POST":
        if not can_edit:
            messages.error(request, "No tenés permiso para modificar el perfil del negocio.")
        elif form.is_valid():
            organization = form.save(commit=False)
            organization.is_business_profile = True
            organization.save()
            messages.success(request, "Perfil del negocio actualizado.")
            return redirect("business_profile")
    return render(request, "inventory/business_profile.html", {"supplier_count": Supplier.objects.filter(active=True).count(), "brand_count": Brand.objects.filter(active=True).count(), "profile": profile, "form": form, "can_edit": can_edit})
