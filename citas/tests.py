from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cita, Paciente


def hoy_mas(dias):
    return timezone.localdate() + timedelta(days=dias)


class BaseTest(TestCase):
    def setUp(self):
        self.paciente = Paciente.objects.create(
            nombre="Ana", apellido="López", edad=34,
            telefono="6641000001", correo="ana@correo.com",
        )

    def datos_paciente(self, **cambios):
        datos = {
            "nombre": "Carlos", "apellido": "Mendoza", "edad": "40",
            "telefono": "6649876543", "correo": "carlos@correo.com",
        }
        datos.update(cambios)
        return datos

    def datos_cita(self, **cambios):
        datos = {
            "paciente": self.paciente.id,
            "fecha": hoy_mas(5).isoformat(),
            "hora": "10:00",
            "motivo": "Consulta general de rutina",
            "estado": Cita.PENDIENTE,
        }
        datos.update(cambios)
        return datos

    def mensajes(self, respuesta):
        return [str(m) for m in get_messages(respuesta.wsgi_request)]


class PruebasPacientes(BaseTest):
    def test_01_registrar_paciente_valido(self):
        r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente())
        self.assertEqual(Paciente.objects.count(), 2)
        self.assertRedirects(r, reverse("detalle_paciente", args=[Paciente.objects.latest("id").id]))
        self.assertIn("Paciente registrado correctamente.", self.mensajes(r))

    def test_02_paciente_edad_negativa(self):
        r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(edad="-5"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("La edad debe estar entre 1 y 120 años.", r.context["form"].errors["edad"])
        self.assertEqual(Paciente.objects.count(), 1)

    def test_03_paciente_edad_fuera_de_rango(self):
        for edad in ("0", "121"):
            r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(edad=edad))
            self.assertIn("edad", r.context["form"].errors)
        for edad in ("1", "120"):
            r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(edad=edad))
            self.assertEqual(r.status_code, 302)

    def test_04_telefono_8_digitos(self):
        r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(telefono="66412345"))
        self.assertIn("El teléfono debe tener exactamente 10 dígitos numéricos.", r.context["form"].errors["telefono"])
        self.assertEqual(Paciente.objects.count(), 1)

    def test_05_telefono_con_letras_o_11_digitos(self):
        for tel in ("66412345ab", "66412345678", "664-123-45"):
            r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(telefono=tel))
            self.assertIn("telefono", r.context["form"].errors)

    def test_06_nombre_y_apellido_minimo_3(self):
        r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(nombre="Al", apellido=" Lu "))
        self.assertIn("nombre", r.context["form"].errors)
        self.assertIn("apellido", r.context["form"].errors)

    def test_07_campos_obligatorios(self):
        r = self.client.post(reverse("paciente_nuevo"), {})
        for campo in ("nombre", "apellido", "edad", "telefono", "correo"):
            self.assertIn(campo, r.context["form"].errors)

    def test_08_correo_invalido(self):
        r = self.client.post(reverse("paciente_nuevo"), self.datos_paciente(correo="no-es-correo"))
        self.assertIn("correo", r.context["form"].errors)

    def test_09_editar_paciente(self):
        r = self.client.post(
            reverse("paciente_editar", args=[self.paciente.id]),
            self.datos_paciente(nombre="Ana María", apellido="López", telefono="6641111111"),
        )
        self.paciente.refresh_from_db()
        self.assertEqual(self.paciente.nombre, "Ana María")
        self.assertIn("Paciente actualizado correctamente.", self.mensajes(r))


class PruebasCitas(BaseTest):
    def test_10_registrar_cita_valida(self):
        r = self.client.post(reverse("cita_nueva"), self.datos_cita())
        self.assertRedirects(r, reverse("lista_citas"))
        self.assertEqual(Cita.objects.count(), 1)
        self.assertIn("Cita médica registrada correctamente.", self.mensajes(r))

    def test_11_cita_fecha_anterior(self):
        r = self.client.post(reverse("cita_nueva"), self.datos_cita(fecha=hoy_mas(-1).isoformat()))
        self.assertIn("fecha", r.context["form"].errors)
        self.assertEqual(Cita.objects.count(), 0)

    def test_12_cita_fecha_hoy_permitida(self):
        r = self.client.post(reverse("cita_nueva"), self.datos_cita(fecha=hoy_mas(0).isoformat()))
        self.assertEqual(r.status_code, 302)

    def test_13_cita_hora_fuera_de_horario(self):
        for hora in ("07:59", "18:01", "23:00"):
            r = self.client.post(reverse("cita_nueva"), self.datos_cita(hora=hora))
            self.assertIn("hora", r.context["form"].errors, hora)
        for hora in ("08:00", "12:30", "18:00"):
            Cita.objects.all().delete()
            r = self.client.post(reverse("cita_nueva"), self.datos_cita(hora=hora))
            self.assertEqual(r.status_code, 302, hora)

    def test_14_cita_motivo_corto(self):
        r = self.client.post(reverse("cita_nueva"), self.datos_cita(motivo="Dolor"))
        self.assertIn("motivo", r.context["form"].errors)

    def test_15_cita_paciente_inexistente(self):
        r = self.client.post(reverse("cita_nueva"), self.datos_cita(paciente=9999))
        self.assertIn("paciente", r.context["form"].errors)

    def test_16_cita_estado_invalido(self):
        r = self.client.post(reverse("cita_nueva"), self.datos_cita(estado="Finalizada"))
        self.assertIn("estado", r.context["form"].errors)

    def test_17_horario_ocupado(self):
        Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                            motivo="Consulta ya registrada", estado=Cita.CONFIRMADA)
        for estado in (Cita.PENDIENTE, Cita.CONFIRMADA):
            r = self.client.post(reverse("cita_nueva"), self.datos_cita(estado=estado))
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.context["form"].has_error("hora", code="horario_ocupado"))
            self.assertIn(
                "No es posible registrar la cita: el horario seleccionado ya está ocupado.",
                self.mensajes(r),
            )
        self.assertEqual(Cita.objects.count(), 1)

    def test_18_cita_cancelada_no_bloquea_horario(self):
        Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                            motivo="Consulta cancelada", estado=Cita.CANCELADA)
        r = self.client.post(reverse("cita_nueva"), self.datos_cita())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Cita.objects.count(), 2)

    def test_19_registrar_cita_cancelada_en_horario_ocupado(self):
        Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                            motivo="Consulta ya registrada", estado=Cita.PENDIENTE)
        r = self.client.post(reverse("cita_nueva"), self.datos_cita(estado=Cita.CANCELADA))
        self.assertEqual(r.status_code, 302)

    def test_20_editar_cita(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        r = self.client.post(
            reverse("cita_editar", args=[cita.id]),
            self.datos_cita(hora="11:00", estado=Cita.CONFIRMADA, motivo="Seguimiento de tratamiento"),
        )
        self.assertRedirects(r, reverse("lista_citas"))
        cita.refresh_from_db()
        self.assertEqual(cita.hora.strftime("%H:%M"), "11:00")
        self.assertEqual(cita.estado, Cita.CONFIRMADA)
        self.assertIn("Cita médica actualizada correctamente.", self.mensajes(r))

    def test_21_editar_cita_sin_cambiar_horario_no_choca_consigo_misma(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        r = self.client.post(reverse("cita_editar", args=[cita.id]),
                             self.datos_cita(estado=Cita.CONFIRMADA))
        self.assertEqual(r.status_code, 302)

    def test_22_editar_cita_a_horario_ocupado(self):
        Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                            motivo="Consulta ya registrada", estado=Cita.CONFIRMADA)
        otra = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="12:00",
                                   motivo="Otra consulta médica", estado=Cita.PENDIENTE)
        r = self.client.post(reverse("cita_editar", args=[otra.id]), self.datos_cita())
        self.assertTrue(r.context["form"].has_error("hora", code="horario_ocupado"))

    def test_23_cancelar_cita(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        r = self.client.post(reverse("cita_cancelar", args=[cita.id]))
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CANCELADA)
        self.assertIn("La cita ha sido cancelada correctamente.", self.mensajes(r))

    def test_24_eliminar_cita(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        r = self.client.post(reverse("cita_eliminar", args=[cita.id]))
        self.assertFalse(Cita.objects.filter(id=cita.id).exists())
        self.assertIn("La cita ha sido eliminada correctamente.", self.mensajes(r))

    def test_25_cancelar_y_eliminar_solo_por_post(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        for nombre in ("cita_cancelar", "cita_eliminar"):
            self.assertEqual(self.client.get(reverse(nombre, args=[cita.id])).status_code, 405)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.PENDIENTE)

    def test_26_proteccion_csrf(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post(reverse("cita_eliminar", args=[cita.id])).status_code, 403)
        self.assertEqual(c.post(reverse("cita_cancelar", args=[cita.id])).status_code, 403)
        self.assertEqual(c.post(reverse("paciente_nuevo"), self.datos_paciente()).status_code, 403)
        self.assertTrue(Cita.objects.filter(id=cita.id, estado=Cita.PENDIENTE).exists())

    def test_27_next_externo_se_ignora(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        r = self.client.post(reverse("cita_cancelar", args=[cita.id]), {"next": "https://malicioso.example/"})
        self.assertRedirects(r, reverse("lista_citas"))

    def test_28_paginas_cargan(self):
        cita = Cita.objects.create(paciente=self.paciente, fecha=hoy_mas(5), hora="10:00",
                                   motivo="Consulta general", estado=Cita.PENDIENTE)
        for nombre, args in [
            ("inicio", []), ("lista_pacientes", []), ("detalle_paciente", [self.paciente.id]),
            ("lista_citas", []), ("citas_pendientes", []), ("paciente_nuevo", []),
            ("paciente_editar", [self.paciente.id]), ("cita_nueva", []), ("cita_editar", [cita.id]),
        ]:
            self.assertEqual(self.client.get(reverse(nombre, args=args)).status_code, 200, nombre)
