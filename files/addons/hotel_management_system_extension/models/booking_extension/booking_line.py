# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelBookingLineExtension(models.Model):
    _inherit = "hotel.booking.line"

    # Sobrescribir el campo booking_days para usar nuestro método de cálculo
    # Cambiado a Float para permitir reservas de pocas horas (fracciones de día)
    booking_days = fields.Float(
        string="Days Book For",
        compute="_compute_booking_days_from_booking",
        store=True,
        copy=False,
        digits=(16, 4),  # Permitir hasta 4 decimales para precisión en horas
        help="Días de reserva (puede ser fraccional para reservas de pocas horas, ej: 0.08 = 2 horas)",
    )

    # =============================================================================
    # CAMPOS DE DESCUENTO
    # =============================================================================

    # Precio original de la habitación, para no perderlo
    original_price = fields.Monetary(
        string="Precio Original",
        readonly=True,
        tracking=True,
        currency_field="currency_id",
        help="Precio original de la habitación antes de cualquier descuento",
    )

    # Monto del descuento aplicado
    discount_amount = fields.Monetary(
        string="Monto Descontado",
        readonly=True,
        tracking=True,
        currency_field="currency_id",
        help="Monto total del descuento aplicado a la línea de reserva",
    )

    # Razón del descuento
    discount_reason = fields.Text(
        string="Razón del Descuento/Cambio",
        tracking=True,
        help="Explicación del motivo del descuento o cambio de precio",
    )

    # Campo temporal para controlar el wizard
    _need_price_wizard = fields.Boolean(
        string="Necesita Wizard de Precio",
        default=False,
        help="Campo temporal para controlar la apertura del wizard de cambio de precio",
    )

    # Campos para cambio de habitación
    is_room_change_segment = fields.Boolean(
        string="Room Change Segment",
        default=False,
        help="Indicates this line is part of a room change",
    )

    previous_line_id = fields.Many2one(
        "hotel.booking.line",
        string="Previous Line",
        help="Previous booking line in the room change sequence",
    )

    next_line_id = fields.Many2one(
        "hotel.booking.line",
        string="Next Line",
        help="Next booking line in the room change sequence",
    )

    @api.depends(
        "booking_id.booking_days", "booking_id.check_in", "booking_id.check_out"
    )
    def _compute_booking_days_from_booking(self):
        """
        Calcular booking_days basado en la reserva principal
        """
        for line in self:
            if not line.booking_id:
                line.booking_days = 0
                continue

            # Si la reserva principal ya tiene booking_days calculado, usarlo
            if line.booking_id.booking_days and line.booking_id.booking_days > 0:
                line.booking_days = line.booking_id.booking_days
                continue

            # Si no, calcular desde las fechas
            if line.booking_id.check_in and line.booking_id.check_out:
                try:
                    check_in = line.booking_id.check_in
                    check_out = line.booking_id.check_out

                    # Convertir a datetime si es necesario
                    if isinstance(check_in, str):
                        check_in = fields.Datetime.from_string(check_in)
                    if isinstance(check_out, str):
                        check_out = fields.Datetime.from_string(check_out)

                    # Calcular días (permitir fracciones para reservas de pocas horas)
                    if hasattr(check_in, "date") and hasattr(check_out, "date"):
                        # Calcular diferencia en días completos
                        days_diff = (check_out.date() - check_in.date()).days

                        # Si es el mismo día o diferencia pequeña, calcular en horas
                        if days_diff == 0:
                            # Mismo día: calcular duración en horas y convertir a fracción de día
                            if isinstance(check_in, datetime) and isinstance(
                                check_out, datetime
                            ):
                                time_diff = check_out - check_in
                                hours = time_diff.total_seconds() / 3600.0
                                # Convertir horas a fracción de día (24 horas = 1 día)
                                line.booking_days = max(
                                    0.01, hours / 24.0
                                )  # Mínimo 0.01 días (14.4 minutos) para visualización
                            else:
                                line.booking_days = (
                                    0.5  # Medio día por defecto si no se puede calcular
                                )
                        else:
                            # Múltiples días: calcular con precisión de horas
                            if isinstance(check_in, datetime) and isinstance(
                                check_out, datetime
                            ):
                                time_diff = check_out - check_in
                                total_hours = time_diff.total_seconds() / 3600.0
                                line.booking_days = max(
                                    0.01, total_hours / 24.0
                                )  # Convertir a días fraccionales
                            else:
                                line.booking_days = max(
                                    0.01, days_diff
                                )  # Mínimo 0.01 días
                    else:
                        line.booking_days = 0.5  # Medio día por defecto
                except Exception:
                    line.booking_days = 0
            else:
                line.booking_days = 0

    @api.depends(
        "price", "discount", "tax_ids", "booking_days", "booking_id.currency_id"
    )
    def _compute_amount_extension(self):
        """
        Sobrescribir el cálculo de amount para asegurar que funcione correctamente
        """
        for line in self:
            # Asegurar que booking_days esté calculado
            if not line.booking_days and line.booking_id:
                line._compute_booking_days_from_booking()

            # El precio (line.price) es el precio por noche (new_price)
            # El cálculo es simple: precio por noche * días de reserva
            # NO aplicar descuento adicional porque new_price ya es el precio final por noche
            price_per_night = line.price or 0.0

            # Calcular impuestos
            if line.tax_ids and line.booking_id and line.booking_id.currency_id:
                taxes = line.tax_ids.compute_all(
                    price_per_night,
                    line.booking_id.currency_id,
                    1,
                    product=line.product_id,
                )
                line.subtotal_price = taxes["total_excluded"] * line.booking_days
                line.taxed_price = taxes["total_included"] * line.booking_days
            else:
                # Si no hay impuestos, usar el precio directo
                line.subtotal_price = price_per_night * line.booking_days
                line.taxed_price = price_per_night * line.booking_days

    def _compute_amount(self):
        """
        Sobrescribir el método original para usar nuestra lógica mejorada
        """
        self._compute_amount_extension()

    @api.onchange("booking_days")
    def _onchange_booking_days(self):
        """
        Recalcular el subtotal cuando cambia booking_days
        """
        if self.booking_days and self.booking_days > 0.0 and self.price:
            self._compute_amount()

    @api.onchange("price", "discount", "tax_ids")
    def _onchange_price_discount_taxes(self):
        """
        Recalcular el subtotal cuando cambian precio, descuento o impuestos
        """
        if self.price and self.booking_days and self.booking_days > 0.0:
            self._compute_amount()

    @api.onchange("product_id")
    def _onchange_product_id_set_original_price(self):
        """
        Establecer el precio original cuando se selecciona una habitación
        """
        if self.product_id:
            # Usar el precio de lista del template del producto como precio original
            if self.product_id.product_tmpl_id:
                original_price = self.product_id.product_tmpl_id.list_price or 0
                if original_price > 0:
                    self.original_price = original_price
                    # Si no hay precio establecido, usar el precio original
                    if not self.price:
                        self.price = original_price
                else:
                    # Fallback al precio del producto si el template no tiene precio
                    product_price = self.product_id.list_price or 0
                    if product_price > 0:
                        self.original_price = product_price
                        if not self.price:
                            self.price = product_price

    @api.onchange("price")
    def _onchange_price_calculate_discount(self):
        """
        Calcular descuento cuando se cambia el precio manualmente
        """
        if self.original_price > 0 and self.price:
            if self.price < self.original_price:
                # Si el nuevo precio es menor, calcula el descuento
                self.discount_amount = self.original_price - self.price
                # Si no hay razón especificada, usar una por defecto
                if not self.discount_reason:
                    self.discount_reason = "Descuento manual aplicado"
            elif self.price > self.original_price:
                # Si el precio es mayor, no hay descuento
                self.discount_amount = 0.0
                if not self.discount_reason:
                    self.discount_reason = "Precio aumentado manualmente"
            else:
                # Si el precio es igual al original, no hay descuento
                self.discount_amount = 0.0
                if not self.discount_reason:
                    self.discount_reason = ""

    def action_open_price_change_wizard(self):
        """
        Abrir wizard para capturar motivo del cambio de precio
        """
        self.ensure_one()

        # Guardar el precio original si no está establecido
        if not self.original_price and self.price:
            self.original_price = self.price

        # Calcular precio original robusto si no está disponible
        if not self.original_price or self.original_price == 0:
            # Intentar calcular usando lista de precios
            if self.booking_id and self.booking_id.pricelist_id and self.product_id:
                try:
                    pricelist = self.booking_id.pricelist_id
                    partner = self.booking_id.partner_id
                    date = self.booking_id.check_in or fields.Date.today()

                    pricelist_price = pricelist.get_product_price(
                        self.product_id,
                        1,
                        partner=partner,
                        date=date,
                        uom_id=self.product_id.uom_id.id,
                    )

                    if pricelist_price and pricelist_price > 0:
                        self.original_price = pricelist_price
                except Exception:
                    # Fallback al precio de lista del producto
                    if self.product_id.product_tmpl_id.list_price:
                        self.original_price = self.product_id.product_tmpl_id.list_price
                    elif self.product_id.list_price:
                        self.original_price = self.product_id.list_price

        return {
            "type": "ir.actions.act_window",
            "name": _("Cambio de Precio - %s") % (self.product_id.name or "Habitación"),
            "res_model": "hotel.booking.line.price.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_booking_line_id": self.id,
                "booking_line_id": self.id,  # Para compatibilidad con el wizard
                "default_original_price": self.original_price or self.price,
                "default_new_price": self.price,
            },
        }

    @api.onchange("discount_reason")
    def _onchange_discount_reason_validation(self):
        """
        Validar que si hay descuento, debe haber una razón
        """
        if self.discount_amount > 0 and not self.discount_reason:
            return {
                "warning": {
                    "title": _("Razón de Descuento Requerida"),
                    "message": _(
                        "Por favor especifique la razón del descuento aplicado."
                    ),
                }
            }

    def write(self, vals):
        """
        Sobrescribir write para manejar cambios en campos calculados
        """
        result = super().write(vals)

        # Solo recalcular si es necesario y no viene del modal
        if not self.env.context.get("is_add_rooms_modal") and any(
            field in vals for field in ["price", "discount", "tax_ids"]
        ):
            for line in self:
                if line.booking_id and line.price:
                    # Solo recalcular si hay datos válidos
                    line._compute_amount()

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir create para crear automáticamente la reserva principal
        cuando se crea una línea desde el Gantt
        """
        # Crear las líneas primero
        lines = super().create(vals_list)

        # Solo crear reserva automáticamente si viene del Gantt
        # NO crear automáticamente si está en el modal de Add Rooms
        if self.env.context.get("from_gantt") and not self.env.context.get(
            "is_add_rooms_modal"
        ):
            for line in lines:
                if not line.booking_id:
                    line._create_booking_from_gantt()

        return lines

    @api.model
    def default_get(self, fields_list):
        """
        Sobrescribir default_get para pre-llenar Members Details con datos del huésped principal
        """
        res = super().default_get(fields_list)

        # Solo aplicar si estamos en el contexto del modal Add Rooms
        if self.env.context.get("is_add_rooms_modal"):
            guest_name = self.env.context.get("default_guest_name")
            guest_email = self.env.context.get("default_guest_email")
            guest_phone = self.env.context.get("default_guest_phone")
            partner_id = self.env.context.get("default_partner_id")

            # Establecer booking_days desde el contexto
            if "booking_days" in fields_list:
                res["booking_days"] = self.env.context.get("default_booking_days", 1)

            # Si tenemos datos del huésped, crear un registro guest_info por defecto
            if guest_name and "guest_info_ids" in fields_list:
                # Crear datos por defecto para guest_info_ids
                guest_info_vals = {
                    "name": guest_name,
                    "age": 30,  # Edad por defecto
                    "gender": "male",  # Género por defecto
                }

                # Si hay un partner_id, incluirlo
                if partner_id:
                    guest_info_vals["partner_id"] = partner_id

                # Agregar el registro guest_info por defecto
                res["guest_info_ids"] = [(0, 0, guest_info_vals)]

        return res

    def _create_booking_from_gantt(self):
        """
        Crear la reserva principal desde datos temporales del Gantt
        """
        self.ensure_one()

        # Obtener datos temporales del contexto
        temp_check_in = self.env.context.get("temp_check_in")
        temp_check_out = self.env.context.get("temp_check_out")
        temp_hotel_id = self.env.context.get("temp_hotel_id")
        temp_user_id = self.env.context.get("temp_user_id")
        temp_partner_id = self.env.context.get("temp_partner_id")

        if temp_check_in and temp_check_out:  # Solo crear si hay fechas
            booking_vals = {
                "partner_id": temp_partner_id or False,
                "check_in": temp_check_in,
                "check_out": temp_check_out,
                "hotel_id": temp_hotel_id or False,
                "user_id": temp_user_id or self.env.user.id,
                "status_bar": "initial",  # Estado inicial
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }

            # Crear la reserva principal
            new_booking = self.env["hotel.booking"].create(booking_vals)

            # Asignar la línea a la nueva reserva
            self.write({"booking_id": new_booking.id})

            # Crear mensaje de seguimiento
            new_booking.message_post(
                body=_("Reserva creada desde Gantt - Línea de habitación."),
                subject=_("Reserva Creada desde Gantt"),
            )

            return new_booking

        return False

    def action_cancel_add_rooms(self):
        """
        Método para manejar la cancelación del modal de Add Rooms
        Elimina cualquier línea de reserva creada temporalmente
        """
        # Buscar líneas de reserva sin booking_id (temporales) creadas recientemente por el usuario actual
        temp_lines = self.search(
            [
                ("booking_id", "=", False),
                ("create_uid", "=", self.env.user.id),
                ("create_date", ">=", fields.Datetime.now() - timedelta(minutes=5)),
            ]
        )

        # Eliminar las líneas temporales
        if temp_lines:
            temp_lines.unlink()

        return {"type": "ir.actions.act_window_close"}

    def action_open_change_room_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Change Room"),
            "res_model": "hotel.booking.line.change.room.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_booking_line_id": self.id,
                "default_booking_id": self.booking_id.id,
            },
        }

    def action_request_cleaning(self):
        """Acción específica para solicitar limpieza después del checkout desde booking line"""
        self.ensure_one()
        if self.booking_id and self.booking_id.status_bar == "checkout":
            self.booking_id.status_bar = "cleaning_needed"
            # Agregar mensaje en el chatter
            self.booking_id.message_post(
                body=f"Limpieza solicitada después del checkout por {self.env.user.name}",
                message_type="notification",
            )
        return True
