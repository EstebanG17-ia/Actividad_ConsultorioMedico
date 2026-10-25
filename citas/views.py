from django.shortcuts import get_object_or_404, render

from .models import Cita, Paciente


def inicio(request):
    contexto = {
        "total_pacientes": Paciente.objects.count(),
        "total_citas": Cita.objects.count(),
        "total_pendientes": Cita.objects.filter(estado=Cita.PENDIENTE).count(),
    }
    return render(request, "citas/inicio.html", contexto)


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
