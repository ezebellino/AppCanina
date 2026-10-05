from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from grooming.models import GroomingAppointment
from inventory.models import Product
from patients.models import Patient, PatientContact

from .forms import CartProductForm, CartServiceForm, CashCloseForm, CashMovementForm, CashOpenForm, CheckoutForm, ConsultationChargeForm
from .models import CashMovement, CashSession, Sale, SaleLine


def _cart(request):
    return request.session.setdefault("sale_cart", [])


def _primary_contact(patient):
    if not patient:
        return None
    relation = PatientContact.objects.select_related("contact").filter(patient=patient, is_primary=True).first()
    return relation.contact if relation else None


def _sale_response(request, product_form, service_form, checkout_form, cart, total, linked_appointment=None, linked_consultation_patient=None):
    return render(request, "sales/sale_form.html", {
        "product_form": product_form,
        "service_form": service_form,
        "checkout_form": checkout_form,
        "cart": enumerate(cart),
        "total": total,
        "linked_appointment": linked_appointment,
        "linked_consultation_patient": linked_consultation_patient,
        "product_categories": Product.Category.choices,
    })


def _cash_summary(session):
    sales = list(session.sales.all())
    payment_totals = {
        Sale.PaymentMethod.CASH: sum((sale.total for sale in sales if sale.payment_method == Sale.PaymentMethod.CASH), Decimal("0")),
        Sale.PaymentMethod.TRANSFER: sum((sale.total for sale in sales if sale.payment_method == Sale.PaymentMethod.TRANSFER), Decimal("0")),
        Sale.PaymentMethod.QR: sum((sale.total for sale in sales if sale.payment_method == Sale.PaymentMethod.QR), Decimal("0")),
    }
    movements = list(session.movements.all())
    manual_income = sum((movement.amount for movement in movements if movement.kind == CashMovement.Kind.INCOME), Decimal("0"))
    withdrawals = sum((movement.amount for movement in movements if movement.kind == CashMovement.Kind.WITHDRAWAL), Decimal("0"))
    return {"cash_sales": payment_totals[Sale.PaymentMethod.CASH], "transfer_sales": payment_totals[Sale.PaymentMethod.TRANSFER], "qr_sales": payment_totals[Sale.PaymentMethod.QR], "manual_income": manual_income, "withdrawals": withdrawals, "expected": session.opening_amount + payment_totals[Sale.PaymentMethod.CASH] + manual_income - withdrawals}


def _closed_cash_history():
    history = []
    for session in CashSession.objects.filter(closed_at__isnull=False).prefetch_related("movements", "sales")[:8]:
        summary = _cash_summary(session)
        summary["session"] = session
        summary["difference"] = (session.closing_amount or Decimal("0")) - summary["expected"]
        history.append(summary)
    return history


@login_required
@permission_required("sales.add_sale", raise_exception=True)
@permission_required("grooming.view_groomingappointment", raise_exception=True)
def sale_create_from_appointment(request, appointment_id):
    appointment = get_object_or_404(GroomingAppointment.objects.select_related("patient", "service").prefetch_related("additional_services"), pk=appointment_id)
    if appointment.status != GroomingAppointment.Status.DONE:
        messages.error(request, "Solo podés cobrar turnos finalizados.")
        return redirect("grooming_agenda")
    if Sale.objects.filter(grooming_appointment=appointment).exists():
        messages.error(request, "Este turno ya tiene una venta registrada.")
        return redirect("grooming_agenda")
    if _cart(request):
        messages.error(request, "Terminá o vaciá el carrito actual antes de cargar un turno.")
        return redirect("sale_create")
    services = [appointment.service, *appointment.additional_services.all()]
    if any(service.price <= 0 for service in services):
        messages.error(request, "Configurá el precio sugerido de todos los servicios del turno antes de cobrarlo.")
        return redirect("grooming_service_list")
    request.session["sale_cart"] = [{"kind": "service", "id": service.id, "description": service.name, "quantity": "1", "unit_price": str(service.price), "total": str(service.price)} for service in services]
    request.session["sale_appointment_id"] = appointment.id
    request.session.modified = True
    messages.success(request, f"Se cargaron los servicios del turno de {appointment.patient.name}.")
    return redirect("sale_create")


@login_required
@permission_required("sales.add_sale", raise_exception=True)
def sale_create(request):
    cart = _cart(request)
    product_form, service_form, checkout_form = CartProductForm(), CartServiceForm(), CheckoutForm()
    linked_appointment = None
    linked_consultation_patient = None
    appointment_id = request.session.get("sale_appointment_id")
    if appointment_id:
        linked_appointment = GroomingAppointment.objects.select_related("patient").filter(pk=appointment_id).first()
        if linked_appointment:
            primary_contact = _primary_contact(linked_appointment.patient)
            checkout_form = CheckoutForm(initial={"patient": linked_appointment.patient_id, "contact": primary_contact.id if primary_contact else None})
    consultation_patient_id = request.session.get("sale_consultation_patient_id")
    if consultation_patient_id and not linked_appointment:
        linked_consultation_patient = Patient.objects.filter(pk=consultation_patient_id, active=True).first()
        if linked_consultation_patient:
            primary_contact = _primary_contact(linked_consultation_patient)
            checkout_form = CheckoutForm(initial={"patient": linked_consultation_patient.id, "contact": primary_contact.id if primary_contact else None})
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "product":
            product_form = CartProductForm(request.POST)
            if product_form.is_valid():
                product = product_form.cleaned_data["product"]
                quantity = product_form.cleaned_data["amount"]
                cart.append({"kind": "product", "id": product.id, "description": product.display_name, "quantity": str(quantity), "unit_price": str(product.current_price), "total": str((product.current_price * quantity).quantize(Decimal("0.01")))})
                request.session.modified = True
                return redirect("sale_create")
        elif action == "service":
            service_form = CartServiceForm(request.POST)
            if service_form.is_valid():
                service = service_form.cleaned_data["service"]
                price = service_form.cleaned_data["price"]
                cart.append({"kind": "service", "id": service.id, "description": service.name, "quantity": "1", "unit_price": str(price), "total": str(price)})
                request.session.modified = True
                return redirect("sale_create")
        elif action == "remove":
            index = int(request.POST.get("index", -1))
            if 0 <= index < len(cart): cart.pop(index); request.session.modified = True
            return redirect("sale_create")
        elif action == "checkout":
            checkout_form = CheckoutForm(request.POST)
            if checkout_form.is_valid() and cart:
                if linked_appointment and (linked_appointment.status != GroomingAppointment.Status.DONE or Sale.objects.filter(grooming_appointment=linked_appointment).exists()):
                    checkout_form.add_error(None, "El turno vinculado ya no está disponible para cobrar.")
                    return _sale_response(request, product_form, service_form, checkout_form, cart, sum((Decimal(item["total"]) for item in cart), Decimal("0")), linked_appointment)
                with transaction.atomic():
                    total = Decimal("0")
                    payment_method = checkout_form.cleaned_data["payment_method"]
                    cash_session = CashSession.objects.filter(closed_at__isnull=True).first()
                    if payment_method == Sale.PaymentMethod.CASH and not cash_session:
                        checkout_form.add_error("payment_method", "Abrí una caja antes de registrar ventas en efectivo.")
                        return _sale_response(request, product_form, service_form, checkout_form, cart, sum((Decimal(item["total"]) for item in cart), Decimal("0")), linked_appointment)
                    patient = linked_appointment.patient if linked_appointment else linked_consultation_patient or checkout_form.cleaned_data["patient"]
                    contact = checkout_form.cleaned_data["contact"] or _primary_contact(patient)
                    sale = Sale.objects.create(patient=patient, contact=contact, total=0, payment_method=payment_method, payment_reference=checkout_form.cleaned_data["payment_reference"], seller=request.user, cash_session=cash_session, grooming_appointment=linked_appointment)
                    for item in cart:
                        quantity, price = Decimal(item["quantity"]), Decimal(item["unit_price"])
                        if item["kind"] == "product":
                            product = Product.objects.select_for_update().get(pk=item["id"])
                            if quantity > product.stock: raise ValueError(f"Stock insuficiente: {product.name}")
                            product.stock -= quantity; product.save(update_fields=["stock"])
                            SaleLine.objects.create(sale=sale, product=product, description=item["description"], quantity=quantity, unit_price=price, total=Decimal(item["total"]))
                        elif item["kind"] == "service":
                            from grooming.models import GroomingService
                            SaleLine.objects.create(sale=sale, service=GroomingService.objects.get(pk=item["id"]), description=item["description"], quantity=quantity, unit_price=price, total=Decimal(item["total"]))
                        else:
                            SaleLine.objects.create(sale=sale, description=item["description"], quantity=quantity, unit_price=price, total=Decimal(item["total"]))
                        total += Decimal(item["total"])
                    sale.total = total; sale.save(update_fields=["total"])
                request.session["sale_cart"] = []
                request.session.pop("sale_appointment_id", None)
                request.session.pop("sale_consultation_patient_id", None)
                messages.success(request, f"Venta registrada por ${total}.")
                return redirect("sale_create")
    total = sum((Decimal(item["total"]) for item in cart), Decimal("0"))
    return _sale_response(request, product_form, service_form, checkout_form, cart, total, linked_appointment, linked_consultation_patient)


@login_required
@permission_required("sales.add_sale", raise_exception=True)
@permission_required("patients.view_patient", raise_exception=True)
def consultation_charge(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id, active=True)
    form = ConsultationChargeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if _cart(request):
            messages.error(request, "Terminá o vaciá el carrito actual antes de cargar una consulta.")
            return redirect("sale_create")
        detail = form.cleaned_data["detail"].strip() or "Consulta veterinaria"
        amount = form.cleaned_data["amount"]
        request.session["sale_cart"] = [{"kind": "consultation", "description": detail, "quantity": "1", "unit_price": str(amount), "total": str(amount)}]
        request.session["sale_consultation_patient_id"] = patient.id
        request.session.modified = True
        messages.success(request, f"Consulta de {patient.name} preparada para cobrar.")
        return redirect("sale_create")
    return render(request, "sales/consultation_charge_form.html", {"patient": patient, "form": form})


@login_required
@permission_required("sales.view_sale", raise_exception=True)
def sale_list(request):
    return render(request, "sales/sale_list.html", {"sales": Sale.objects.prefetch_related("lines").select_related("seller", "patient", "contact")[:30]})


@login_required
@permission_required("sales.view_sale", raise_exception=True)
def daily_report(request):
    """A compact closing view for the current operating day."""
    today = timezone.localdate()
    sales = Sale.objects.filter(created_at__date=today).select_related("patient", "contact", "seller").prefetch_related("lines")
    payment_totals = {
        method: sales.filter(payment_method=method).aggregate(total=Sum("total"))["total"] or Decimal("0")
        for method, _label in Sale.PaymentMethod.choices
    }
    total = sum(payment_totals.values(), Decimal("0"))
    top_lines = (
        SaleLine.objects.filter(sale__created_at__date=today)
        .values("description")
        .annotate(quantity=Sum("quantity"), total=Sum("total"))
        .order_by("-total", "description")[:5]
    )
    cash_session = CashSession.objects.filter(closed_at__isnull=True).prefetch_related("movements", "sales").first()
    cash_summary = _cash_summary(cash_session) if cash_session else None
    return render(request, "sales/daily_report.html", {
        "today": today,
        "sales": sales,
        "sales_count": sales.count(),
        "payment_totals": payment_totals,
        "total": total,
        "top_lines": top_lines,
        "cash_session": cash_session,
        "cash_summary": cash_summary,
    })


@login_required
@permission_required("sales.view_cashsession", raise_exception=True)
def cash_dashboard(request):
    session = CashSession.objects.filter(closed_at__isnull=True).prefetch_related("movements", "sales").first()
    if not session:
        form = CashOpenForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            CashSession.objects.create(opened_by=request.user, opening_amount=form.cleaned_data["opening_amount"])
            messages.success(request, "Caja abierta.")
            return redirect("cash_dashboard")
        return render(request, "sales/cash_open.html", {"form": form, "closed_sessions": _closed_cash_history()})
    summary = _cash_summary(session)
    movement_form, close_form = CashMovementForm(), CashCloseForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "movement":
            movement_form = CashMovementForm(request.POST)
            if movement_form.is_valid():
                CashMovement.objects.create(session=session, **movement_form.cleaned_data)
                return redirect("cash_dashboard")
        elif action == "close":
            close_form = CashCloseForm(request.POST)
            if close_form.is_valid():
                session.closed_at = timezone.now(); session.closing_amount = close_form.cleaned_data["closing_amount"]; session.closing_notes = close_form.cleaned_data["closing_notes"]; session.save()
                messages.success(request, f"Caja cerrada. Diferencia: ${session.closing_amount - summary['expected']}.")
                return redirect("cash_dashboard")
    return render(request, "sales/cash_dashboard.html", {"session": session, "summary": summary, "movement_form": movement_form, "close_form": close_form})
