import re
from datetime import time

from django import forms
from django.utils import timezone

from .models import Cita, Paciente

# Horario de atención permitido para las citas (ambos extremos incluidos).
HORA_APERTURA = time(8, 0)
HORA_CIERRE = time(18, 0)

# Estados que "ocupan" un horario. Una cita Cancelada no bloquea la agenda.
ESTADOS_ACTIVOS = [Cita.PENDIENTE, Cita.CONFIRMADA]

MENSAJE_HORARIO_OCUPADO = (
    "No es posible registrar la cita: el horario seleccionado ya está ocupado."
)


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ["nombre", "apellido", "edad", "telefono", "correo"]
        labels = {
            "nombre": "Nombre",
            "apellido": "Apellido",
            "edad": "Edad",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej. Ana"}),
            "apellido": forms.TextInput(attrs={"placeholder": "Ej. López"}),
            "edad": forms.NumberInput(attrs={"placeholder": "1 a 120"}),
            "telefono": forms.TextInput(
                attrs={"placeholder": "10 dígitos, ej. 6641234567", "inputmode": "numeric"}
            ),
            "correo": forms.EmailInput(attrs={"placeholder": "nombre@correo.com"}),
        }
        error_messages = {
            "nombre": {"required": "El nombre es obligatorio."},
            "apellido": {"required": "El apellido es obligatorio."},
            "edad": {
                "required": "La edad es obligatoria.",
                "invalid": "Ingresa una edad válida (número entero).",
            },
            "telefono": {"required": "El teléfono es obligatorio."},
            "correo": {
                "required": "El correo electrónico es obligatorio.",
                "invalid": "Ingresa un correo electrónico con formato válido.",
            },
        }

    # --- Validaciones en el backend (no dependen del HTML) -----------------
    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data["apellido"].strip()
        if len(apellido) < 3:
            raise forms.ValidationError("El apellido debe tener al menos 3 caracteres.")
        return apellido

    def clean_edad(self):
        edad = self.cleaned_data["edad"]
        if edad < 1 or edad > 120:
            raise forms.ValidationError("La edad debe estar entre 1 y 120 años.")
        return edad

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"].strip()
        if not re.fullmatch(r"[0-9]{10}", telefono):
            raise forms.ValidationError(
                "El teléfono debe tener exactamente 10 dígitos numéricos."
            )
        return telefono


class CitaForm(forms.ModelForm):
    class Meta:
        model = Cita
        fields = ["paciente", "fecha", "hora", "motivo", "estado"]
        labels = {
            "paciente": "Paciente",
            "fecha": "Fecha",
            "hora": "Hora",
            "motivo": "Motivo de consulta",
            "estado": "Estado",
        }
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "motivo": forms.TextInput(
                attrs={"placeholder": "Describe el motivo (mínimo 10 caracteres)"}
            ),
        }
        error_messages = {
            "paciente": {
                "required": "Selecciona un paciente.",
                "invalid_choice": "Selecciona un paciente previamente registrado.",
            },
            "fecha": {
                "required": "La fecha es obligatoria.",
                "invalid": "Ingresa una fecha válida.",
            },
            "hora": {
                "required": "La hora es obligatoria.",
                "invalid": "Ingresa una hora válida.",
            },
            "motivo": {"required": "El motivo de consulta es obligatorio."},
            "estado": {
                "required": "Selecciona el estado de la cita.",
                "invalid_choice": "Estado no válido. Elige Pendiente, Confirmada o Cancelada.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo pacientes ya registrados (ModelChoiceField valida contra este queryset).
        self.fields["paciente"].queryset = Paciente.objects.all()
        self.fields["paciente"].empty_label = "— Selecciona un paciente —"

    # --- Validaciones por campo ---------------------------------------------
    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        # Al editar una cita sin cambiar su fecha se respeta la fecha original
        # (por ejemplo, para confirmar o corregir una cita que ya pasó).
        fecha_sin_cambios = self.instance.pk and fecha == self.instance.fecha
        if fecha < timezone.localdate() and not fecha_sin_cambios:
            raise forms.ValidationError(
                "No se pueden registrar citas en fechas anteriores a la actual."
            )
        return fecha

    def clean_hora(self):
        hora = self.cleaned_data["hora"]
        if hora < HORA_APERTURA or hora > HORA_CIERRE:
            raise forms.ValidationError(
                "Las citas solo pueden programarse entre las 8:00 y las 18:00 horas."
            )
        return hora

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if len(motivo) < 10:
            raise forms.ValidationError(
                "El motivo de consulta debe tener al menos 10 caracteres."
            )
        return motivo

    # --- Validación de disponibilidad (solo ORM, sin SQL manual) -----------
    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get("fecha")
        hora = cleaned.get("hora")
        estado = cleaned.get("estado")

        # Solo se valida si los campos anteriores son correctos y la cita
        # quedaría activa (Pendiente o Confirmada).
        if fecha and hora and estado in ESTADOS_ACTIVOS:
            ocupado = (
                Cita.objects.filter(
                    fecha=fecha, hora=hora, estado__in=ESTADOS_ACTIVOS
                )
                .exclude(pk=self.instance.pk)  # al editar, no choca consigo misma
                .exists()
            )
            if ocupado:
                self.add_error(
                    "hora",
                    forms.ValidationError(
                        "El horario seleccionado ya está ocupado.",
                        code="horario_ocupado",
                    ),
                )
        return cleaned
