from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    # Pacientes
    path("pacientes/", views.lista_pacientes, name="lista_pacientes"),
    path("pacientes/nuevo/", views.paciente_nuevo, name="paciente_nuevo"),
    path("pacientes/<int:id>/", views.detalle_paciente, name="detalle_paciente"),
    path("pacientes/<int:id>/editar/", views.paciente_editar, name="paciente_editar"),
    # Citas
    path("citas/", views.lista_citas, name="lista_citas"),
    path("citas/pendientes/", views.citas_pendientes, name="citas_pendientes"),
    path("citas/nueva/", views.cita_nueva, name="cita_nueva"),
    path("citas/<int:id>/editar/", views.cita_editar, name="cita_editar"),
    path("citas/<int:id>/cancelar/", views.cita_cancelar, name="cita_cancelar"),
    path("citas/<int:id>/eliminar/", views.cita_eliminar, name="cita_eliminar"),
]
