from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("pacientes/", views.lista_pacientes, name="lista_pacientes"),
    path("pacientes/<int:id>/", views.detalle_paciente, name="detalle_paciente"),
    path("citas/", views.lista_citas, name="lista_citas"),
    path("citas/pendientes/", views.citas_pendientes, name="citas_pendientes"),
]
