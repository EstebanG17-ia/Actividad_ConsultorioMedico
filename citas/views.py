from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import MENSAJE_HORARIO_OCUPADO, CitaForm, PacienteForm
from .models import Cita, Paciente


def inicio(request):
    contexto = {
        "total_pacientes": Paciente.objects.count(),
        "total_citas": Cita.objects.count(),
        "total_pendientes": Cita.objects.filter(estado=Cita.PENDIENTE).count(),
    }
    return render(request, "citas/inicio.html", contexto)


# ---------------------------------------------------------------- Pacientes
def lista_pacientes(request):
    pacientes = Paciente.objects.all()
    return render(request, "citas/pacientes_lista.html", {"pacientes": pacientes})


def detalle_paciente(request, id):
    paciente = get_object_or_404(Paciente, id=id)
    citas = paciente.citas.all()
    return render(
        request,
        "citas/paciente_detalle.html",
        {"paciente": paciente, "citas": citas},
    )


def paciente_nuevo(request):
    if request.method == "POST":
        form = PacienteForm(request.POST)
        if form.is_valid():
            paciente = form.save()
            messages.success(request, "Paciente registrado correctamente.")
            return redirect("detalle_paciente", id=paciente.id)
    else:
        form = PacienteForm()
    return render(
        request,
        "citas/formulario.html",
        {
            "form": form,
            "titulo": "Registrar paciente",
            "texto_boton": "Guardar paciente",
            "url_cancelar": "lista_pacientes",
        },
    )


def paciente_editar(request, id):
    paciente = get_object_or_404(Paciente, id=id)
    if request.method == "POST":
        form = PacienteForm(request.POST, instance=paciente)
        if form.is_valid():
            form.save()
            messages.success(request, "Paciente actualizado correctamente.")
            return redirect("detalle_paciente", id=paciente.id)
    else:
        form = PacienteForm(instance=paciente)
    return render(
        request,
        "citas/formulario.html",
        {
            "form": form,
            "titulo": f"Editar paciente: {paciente}",
            "texto_boton": "Guardar cambios",
            "url_cancelar": "detalle_paciente",
            "arg_cancelar": paciente.id,
        },
    )


# -------------------------------------------------------------------- Citas
def lista_citas(request):
    citas = Cita.objects.select_related("paciente").all()
    return render(
        request,
        "citas/citas_lista.html",
        {"citas": citas, "titulo": "Listado general de citas"},
    )


def citas_pendientes(request):
    citas = Cita.objects.select_related("paciente").filter(estado=Cita.PENDIENTE)
    return render(
        request,
        "citas/citas_lista.html",
        {"citas": citas, "titulo": "Citas pendientes"},
    )


def _avisar_si_horario_ocupado(request, form):
    """Muestra además el mensaje general cuando el horario ya está ocupado."""
    if form.has_error("hora", code="horario_ocupado"):
        messages.error(request, MENSAJE_HORARIO_OCUPADO)


def cita_nueva(request):
    if request.method == "POST":
        form = CitaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cita médica registrada correctamente.")
            return redirect("lista_citas")
        _avisar_si_horario_ocupado(request, form)
    else:
        # Permite llegar desde la ficha de un paciente con el paciente elegido.
        inicial = {}
        paciente_id = request.GET.get("paciente")
        if paciente_id and paciente_id.isdigit():
            inicial["paciente"] = paciente_id
        form = CitaForm(initial=inicial)
    return render(
        request,
        "citas/formulario.html",
        {
            "form": form,
            "titulo": "Programar cita médica",
            "texto_boton": "Guardar cita",
            "url_cancelar": "lista_citas",
        },
    )


def cita_editar(request, id):
    cita = get_object_or_404(Cita, id=id)
    if request.method == "POST":
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            form.save()
            messages.success(request, "Cita médica actualizada correctamente.")
            return redirect("lista_citas")
        _avisar_si_horario_ocupado(request, form)
    else:
        form = CitaForm(instance=cita)
    return render(
        request,
        "citas/formulario.html",
        {
            "form": form,
            "titulo": "Editar cita médica",
            "texto_boton": "Guardar cambios",
            "url_cancelar": "lista_citas",
        },
    )


def _destino_seguro(request, por_defecto="lista_citas"):
    """Regresa a la página desde donde se envió la acción (si es segura)."""
    siguiente = request.POST.get("next", "")
    if siguiente and url_has_allowed_host_and_scheme(
        siguiente, allowed_hosts={request.get_host()}
    ):
        return redirect(siguiente)
    return redirect(por_defecto)


@require_POST
def cita_cancelar(request, id):
    cita = get_object_or_404(Cita, id=id)
    if cita.estado == Cita.CANCELADA:
        messages.info(request, "La cita ya se encontraba cancelada.")
    else:
        cita.estado = Cita.CANCELADA
        cita.save(update_fields=["estado"])
        messages.success(request, "La cita ha sido cancelada correctamente.")
    return _destino_seguro(request)


@require_POST
def cita_eliminar(request, id):
    cita = get_object_or_404(Cita, id=id)
    cita.delete()
    messages.success(request, "La cita ha sido eliminada correctamente.")
    return _destino_seguro(request)
