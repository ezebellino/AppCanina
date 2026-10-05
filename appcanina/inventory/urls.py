from django.urls import path

from . import views

urlpatterns = [
    path("", views.product_list, name="inventory_list"),
    path("alertas/", views.inventory_alerts, name="inventory_alerts"),
    path("nuevo/", views.product_create, name="product_create"),
    path("importar/", views.product_import, name="product_import"),
    path("<int:product_id>/editar/", views.product_edit, name="product_edit"),
    path("proveedores/", views.supplier_list, name="supplier_list"),
    path("proveedores/nuevo/", views.supplier_create, name="supplier_create"),
    path("proveedores/<int:supplier_id>/aumentar-precios/", views.supplier_price_increase, name="supplier_price_increase"),
    path("marcas/", views.brand_list, name="brand_list"),
    path("marcas/nueva/", views.brand_create, name="brand_create"),
    path("mi-negocio/", views.business_profile, name="business_profile"),
]
