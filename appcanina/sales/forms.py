from decimal import Decimal

from django import forms

from grooming.models import GroomingService
from inventory.models import Product
from patients.models import Contact, Patient
from .models import Sale


class ProductSaleSelect(forms.Select):
    """Adds product data to each option for the quick sale finder."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        product = getattr(value, "instance", None)
        if product:
            option["attrs"].update({
                "data-category": product.category,
                "data-stock": str(product.stock),
            })
        return option


class CartProductForm(forms.Form):
    product = forms.ModelChoiceField(label="Producto", queryset=Product.objects.filter(active=True), empty_label="Seleccioná un producto")
    grams = forms.DecimalField(label="Gramos", required=False, min_value=Decimal("1"), decimal_places=0, max_digits=8)
    quantity = forms.DecimalField(label="Cantidad", required=False, min_value=Decimal("0.001"), decimal_places=3, max_digits=10)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        product_field = self.fields["product"]
        product_field.queryset = Product.objects.filter(active=True).select_related("brand")
        product_field.widget = ProductSaleSelect(attrs={"class": "sale-product-select"})
        product_field.widget.choices = product_field.choices
        product_field.label_from_instance = lambda product: "{}{} · {} · ${} · Stock: {}".format(
            product.display_name,
            f" · {product.sku}" if product.sku else "",
            product.brand,
            product.current_price,
            product.stock,
        )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        if not product:
            return cleaned
        amount = cleaned.get("grams") / Decimal("1000") if product.sale_unit == Product.SaleUnit.KILOGRAM and cleaned.get("grams") else cleaned.get("quantity")
        if not amount:
            self.add_error("grams" if product.sale_unit == Product.SaleUnit.KILOGRAM else "quantity", "Indicá la cantidad.")
        elif amount > product.stock:
            self.add_error(None, f"Stock insuficiente. Disponible: {product.stock}.")
        cleaned["amount"] = amount
        return cleaned


class CartServiceForm(forms.Form):
    service = forms.ModelChoiceField(label="Servicio", queryset=GroomingService.objects.filter(active=True), empty_label="Seleccioná un servicio")
    price = forms.DecimalField(label="Precio del servicio", min_value=Decimal("0"), decimal_places=2, max_digits=12)


class CheckoutForm(forms.Form):
    patient = forms.ModelChoiceField(label="Paciente", queryset=Patient.objects.filter(active=True), required=False, empty_label="Sin paciente asociado")
    contact = forms.ModelChoiceField(label="Cliente o responsable", queryset=Contact.objects.order_by("full_name"), required=False, empty_label="Usar responsable principal del paciente")
    payment_method = forms.ChoiceField(label="Cobro", choices=Sale.PaymentMethod.choices)
    payment_reference = forms.CharField(label="Referencia", required=False, max_length=120)


class ConsultationChargeForm(forms.Form):
    amount = forms.DecimalField(label="Importe de la consulta", min_value=Decimal("0"), decimal_places=2, max_digits=12)
    detail = forms.CharField(label="Detalle", max_length=180, initial="Consulta veterinaria", required=False)


class CashOpenForm(forms.Form):
    opening_amount = forms.DecimalField(label="Monto inicial", required=False, initial=Decimal("0"), min_value=Decimal("0"), decimal_places=2, max_digits=12)

    def clean_opening_amount(self):
        return self.cleaned_data["opening_amount"] or Decimal("0")


class CashMovementForm(forms.Form):
    kind = forms.ChoiceField(label="Movimiento", choices=(("income", "Ingreso manual"), ("withdrawal", "Retiro de caja")))
    amount = forms.DecimalField(label="Importe", min_value=Decimal("0.01"), decimal_places=2, max_digits=12)
    note = forms.CharField(label="Motivo", max_length=180)


class CashCloseForm(forms.Form):
    closing_amount = forms.DecimalField(label="Efectivo contado", min_value=Decimal("0"), decimal_places=2, max_digits=12)
    closing_notes = forms.CharField(label="Observación", required=False, widget=forms.Textarea)
