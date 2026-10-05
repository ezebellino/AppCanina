from django import forms

from decimal import Decimal

from organizations.models import Organization

from .models import Brand, Product, Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "phone", "email", "visit_frequency", "last_visit_on", "notes", "active"]
        widgets = {"last_visit_on": forms.DateInput(attrs={"type": "date"})}


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "active"]


class ProductForm(forms.ModelForm):
    new_brand = forms.CharField(label="Nueva marca", max_length=100, required=False, help_text="Usalo solo si la marca todavía no existe.")
    class Meta:
        model = Product
        fields = ["sku", "name", "commercial_name", "category", "quality", "brand", "supplier", "sale_unit", "package_weight_kg", "price", "promotional_price", "promotion_starts_on", "promotion_ends_on", "stock", "minimum_stock", "batch", "expires_on", "requires_prescription", "active"]
        help_texts = {"name": "Nombre interno breve para identificarlo en el inventario.", "commercial_name": "Opcional. Ejemplo: nombre completo que figura en el envase o para mostrar al cliente."}
        widgets = {"promotion_starts_on": forms.DateInput(attrs={"type": "date"}), "promotion_ends_on": forms.DateInput(attrs={"type": "date"}), "expires_on": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("promotion_starts_on"), cleaned.get("promotion_ends_on")
        promotional_price = cleaned.get("promotional_price")
        if promotional_price is not None and start and end and end < start:
            self.add_error("promotion_ends_on", "La promoción no puede terminar antes de comenzar.")
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        new_brand = self.cleaned_data.get("new_brand", "").strip()
        if new_brand:
            product.brand, _ = Brand.objects.get_or_create(name__iexact=new_brand, defaults={"name": new_brand})
        if commit:
            product.save()
        return product


class PriceIncreaseForm(forms.Form):
    percentage = forms.DecimalField(label="Aumento porcentual", min_value=Decimal("0.01"), max_value=Decimal("100"), decimal_places=2, max_digits=5, help_text="Ejemplo: 6 para aumentar un 6 %.")


class ProductImportForm(forms.Form):
    file = forms.FileField(label="Archivo Excel", help_text="Formato .xlsx. La primera fila debe contener los títulos de las columnas.")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if not uploaded.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Subí un archivo Excel con extensión .xlsx.")
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo no puede superar los 5 MB.")
        return uploaded
