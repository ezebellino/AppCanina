"""Readable receipts from the amounts and descriptions recorded at checkout."""
from decimal import Decimal
from django.utils import timezone


def money(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def receipt_data(sale):
    code = f"V-{sale.pk:08d}"
    rows = list(sale.lines.order_by("pk"))
    if not rows:
        # Old sales predate SaleLine; keep them readable without inventing items.
        from types import SimpleNamespace
        rows = [SimpleNamespace(description=sale.product.display_name if sale.product else "Venta registrada",
                                quantity=sale.quantity or Decimal("1"),
                                unit_price=sale.unit_price if sale.unit_price is not None else sale.total,
                                total=sale.total)]
    items = [{"description": row.description, "quantity": format(row.quantity.normalize(), "f").replace(".", ","),
              "price": money(row.unit_price), "subtotal": money(row.total)} for row in rows]
    business = sale.organization.name if sale.organization else "Lazuna"
    date = timezone.localtime(sale.created_at).strftime("%d/%m/%Y %H:%M")
    lines = [business, f"COMPROBANTE DE COMPRA · {code}", f"Fecha: {date}"]
    if sale.contact:
        lines.append(f"Cliente: {sale.contact.full_name}")
    if sale.patient:
        lines.append(f"Animal: {sale.patient.name}")
    lines.extend(["", "DETALLE DE LA COMPRA"])
    for item in items:
        description = " ".join(item["description"].split())
        lines.extend([description, f'{item["quantity"]} × $ {item["price"]} = $ {item["subtotal"]}'])
    lines.extend(["", f"TOTAL: $ {money(sale.total)}", f"Medio de pago: {sale.get_payment_method_display()}",
                  "", "Gracias por tu compra.", "Comprobante interno · No válido como factura fiscal."])
    return {"code": code, "business": business, "date": date, "items": items,
            "total": money(sale.total), "text": "\n".join(lines)}
