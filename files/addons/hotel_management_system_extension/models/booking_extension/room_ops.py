# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from .constants import BookingState

_logger = logging.getLogger(__name__)


class HotelBookingExtension(models.Model):
    _inherit = "hotel.booking"

    def action_set_to_draft(self):
        """
        Regresar el estado a initial (borrador)
        Solo disponible en estados 'cancelled', 'no_show'
        """
        self.ensure_one()

        if self.status_bar not in ["cancelled", "no_show"]:
            raise UserError(
                _(
                    "Solo se puede regresar a borrador desde estados cancelados o no show."
                )
            )

        self.write({"status_bar": "initial"})

        # Crear mensaje de seguimiento
        self.message_post(
            body=_("Reserva regresada a estado borrador."),
            subject=_("Reserva en Borrador"),
        )

        return True

    def action_mark_cleaning_needed(self):
        """Marcar habitación para limpieza"""
        return self._change_state(BookingState.CLEANING_NEEDED)

    def action_request_cleaning(self):
        """Acción específica para solicitar limpieza después del checkout"""
        for booking in self:
            if booking.status_bar == "checkout":
                booking.status_bar = "cleaning_needed"
                # Agregar mensaje en el chatter
                booking.message_post(
                    body=f"Limpieza solicitada después del checkout por {self.env.user.name}",
                    message_type="notification",
                )
        return True

    def action_request_cleaning_from_booking(self):
        """Acción para solicitar limpieza desde el header de la reserva"""
        return self.action_request_cleaning()

    def action_mark_room_ready(self):
        """Marcar habitación como lista - NO modificar reserva existente"""
        result = self._change_state(BookingState.ROOM_READY)

        # NO modificar la reserva existente - solo cambiar el estado
        # La reserva original se mantiene intacta para historial

        # Actualizar estado de habitaciones para que estén disponibles
        for line in self.booking_line_ids:
            if hasattr(line.product_id, "room_status"):
                line.product_id.room_status = "available"

        # Crear mensaje de seguimiento
        self.message_post(
            body=_(
                "Habitación marcada como lista. La reserva original se mantiene intacta. Disponible para crear NUEVA reserva."
            ),
            subject=_("Habitación Lista"),
        )

        return result

    def action_reuse_room_ready_booking(self):
        """
        Crear una nueva reserva basada en una reserva en estado 'room_ready'
        """
        self.ensure_one()

        if self.status_bar != "room_ready":
            raise UserError(
                _(
                    'Solo se pueden crear nuevas reservas desde reservas en estado "Habitación Lista".'
                )
            )

        # Crear una nueva reserva basada en la actual
        new_booking_vals = {
            "partner_id": False,  # Se llenará con el nuevo cliente
            "check_in": False,  # Se llenará con las nuevas fechas
            "check_out": False,  # Se llenará con las nuevas fechas
            "hotel_id": self.hotel_id.id if self.hotel_id else False,
            "user_id": self.env.user.id,
            "status_bar": "confirmed",  # Nueva reserva confirmada
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "pricelist_id": self.pricelist_id.id if self.pricelist_id else False,
        }

        # Crear la nueva reserva
        new_booking = self.env["hotel.booking"].create(new_booking_vals)

        # Copiar las líneas de habitación de la reserva original
        for line in self.booking_line_ids:
            new_line_vals = {
                "booking_id": new_booking.id,
                "product_id": line.product_id.id,
                "booking_days": 0,  # Se calculará con las nuevas fechas
                "price": line.price,
                "discount": line.discount,
                "tax_ids": [(6, 0, line.tax_ids.ids)],
            }
            self.env["hotel.booking.line"].create(new_line_vals)

        # Crear mensaje de seguimiento en la reserva original
        self.message_post(
            body=_(
                'Nueva reserva creada: <a href="#" data-oe-model="hotel.booking" data-oe-id="%s">%s</a>'
            )
            % (new_booking.id, new_booking.sequence_id),
            subject=_("Nueva Reserva Creada"),
        )

        # Crear mensaje de seguimiento en la nueva reserva
        new_booking.message_post(
            body=_(
                'Reserva creada desde reserva anterior: <a href="#" data-oe-model="hotel.booking" data-oe-id="%s">%s</a>'
            )
            % (self.id, self.sequence_id),
            subject=_("Reserva Creada desde Anterior"),
        )

        return new_booking

    def action_add_rooms_with_context(self):
        """
        Versión personalizada de action_add_rooms que usa el contexto para pre-llenar la habitación
        """
        self.ensure_one()

        # Asegurar que booking_days esté calculado en la reserva principal
        if not self.booking_days and self.check_in and self.check_out:
            self._compute_booking_days()

        # Obtener el ID de la habitación del contexto
        default_product_id = self.env.context.get("default_product_id")

        # Obtener habitaciones disponibles
        booking = self.env["hotel.booking"].search([])
        product_ids = self.env["product.product"].search(
            [("product_tmpl_id.hotel_id", "!=", self.hotel_id.id)]
        )

        for line in booking:
            filtered_bookings = line.filter_booking_based_on_date(
                self.check_in, self.check_out
            )
            if filtered_bookings:
                product_ids += line.mapped("booking_line_ids.product_id")

        # Si hay una habitación específica en el contexto, filtrar solo esa
        if default_product_id:
            product_ids = self.env["product.product"].browse(default_product_id)

        # Crear el contexto para el formulario de línea de reserva
        line_context = {
            "default_booking_id": self.id,
            "default_product_ids": product_ids.ids,
            "is_add_rooms_modal": True,  # Marcar que es el modal de Add Rooms
            "default_booking_days": self.booking_days
            or 1,  # Usar 1 como valor por defecto si no hay días
        }

        # Agregar la habitación específica si está disponible
        if default_product_id:
            line_context["default_product_id"] = default_product_id

        # Agregar datos del huésped para pre-llenar Members Details
        if self.partner_id:
            line_context["default_guest_name"] = self.partner_id.name
            line_context["default_guest_email"] = self.partner_id.email or ""
            line_context["default_guest_phone"] = self.partner_id.phone or ""
            # Pasar el partner_id para el selector de contactos
            line_context["default_partner_id"] = self.partner_id.id

        # Usar una vista genérica si no existe la específica
        try:
            view_id = self.env.ref(
                "hotel_management_system_extension.view_hotel_booking_line_form_extension"
            ).id
        except Exception:
            # Fallback a vista estándar si no existe la personalizada
            view_id = False

        return {
            "name": _("Add Rooms"),
            "type": "ir.actions.act_window",
            "res_model": "hotel.booking.line",
            "view_mode": "form",
            "view_id": view_id,
            "target": "new",
            "context": line_context,
        }
