# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class HotelBookingExtension(models.Model):
    _inherit = "hotel.booking"

    # =============================================================================
    # CAMPOS DE DESCUENTO Y PRECIO ORIGINAL
    # =============================================================================

    # Precio original de la habitación, para no perderlo
    original_price = fields.Monetary(
        string="Precio Original",
        compute="_compute_original_price",
        store=True,
        readonly=True,
        tracking=True,
        help="Precio original de la habitación antes de cualquier descuento",
    )

    # Monto del descuento aplicado
    discount_amount = fields.Monetary(
        string="Monto Descontado",
        compute="_compute_discount_amount",
        store=True,
        readonly=True,
        tracking=True,
        help="Monto total del descuento aplicado a la reserva (calculado automáticamente)",
    )

    # Razón del descuento
    discount_reason = fields.Text(
        string="Razón del Descuento/Cambio",
        tracking=True,
        help="Explicación del motivo del descuento o cambio de precio",
    )

    @api.depends(
        "booking_line_ids",
        "booking_line_ids.product_id",
        "booking_line_ids.product_id.product_tmpl_id.list_price",
    )
    def _compute_original_price(self):
        """
        Computar el precio original basándose en los precios de lista de los productos
        Este método se ejecuta automáticamente cuando cambian las líneas de reserva
        """
        for record in self:
            total_original = 0.0

            if record.booking_line_ids:
                for line in record.booking_line_ids:
                    if line.product_id and line.product_id.product_tmpl_id:
                        # Usar el precio de lista del template del producto
                        list_price = line.product_id.product_tmpl_id.list_price or 0.0
                        total_original += list_price

            record.original_price = total_original

            # Log para debugging
            if total_original == 0 and record.booking_line_ids:
                _logger.warning(
                    "Booking %s: Original price is 0 but has %s booking lines. "
                    "Check product list prices.",
                    record.id,
                    len(record.booking_line_ids),
                )

    @api.onchange("booking_line_ids")
    def _onchange_booking_line_ids_for_price(self):
        """
        Vigilar cambios en las líneas de reserva para actualizar razón del descuento
        El descuento se calcula automáticamente por el campo computado
        """
        if self.booking_line_ids:
            # Solo actualizar la razón del descuento si hay descuento y no hay razón
            if self.discount_amount > 0 and not self.discount_reason:
                self.discount_reason = "Descuento aplicado"
            elif self.discount_amount == 0.0:
                self.discount_reason = ""

    @api.onchange("discount_reason")
    def _onchange_discount_reason(self):
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

    def _set_original_price_from_room(self, room_line):
        """
        Establecer el precio original basado en una línea de habitación específica
        """
        if room_line and room_line.product_id:
            # Obtener el precio de la habitación
            room_price = room_line.price or room_line.product_id.list_price
            if room_price > 0:
                self.original_price = room_price
                # Si no hay descuento, el precio total es igual al original
                if not self.discount_amount:
                    self.discount_amount = 0.0

    def _compute_original_price_from_booking_lines(self):
        """
        Método legacy mantenido para compatibilidad
        Ahora solo fuerza el recálculo del campo computado
        """
        # Forzar recálculo del campo computado
        self._compute_original_price()
        return self.original_price

    @api.depends(
        "booking_line_ids",
        "booking_line_ids.discount_amount",
        "booking_line_ids.original_price",
        "booking_line_ids.price",
    )
    def _compute_discount_amount(self):
        """
        Computar el monto total descontado basándose en las líneas de reserva
        Este método se ejecuta automáticamente cuando cambian los precios o descuentos
        """
        for record in self:
            total_discount = 0.0

            if record.booking_line_ids:
                for line in record.booking_line_ids:
                    # Calcular descuento por línea
                    line_discount = 0.0
                    if line.original_price and line.price:
                        if line.original_price > line.price:
                            line_discount = line.original_price - line.price

                    total_discount += line_discount

            record.discount_amount = total_discount

            # Log para debugging
            _logger.info(
                "Booking %s: Discount amount computed: %s (from %s lines)",
                record.id,
                total_discount,
                len(record.booking_line_ids),
            )

    def force_compute_discount_amount(self):
        """
        Método para forzar el recálculo del descuento
        Útil para corregir reservas existentes con descuentos incorrectos
        """
        self.ensure_one()

        # Forzar recálculo
        self._compute_discount_amount()

        # Log del resultado
        _logger.info(
            "Booking %s: Forced discount computation. Result: %s (from %s lines)",
            self.id,
            self.discount_amount,
            len(self.booking_line_ids),
        )

        return self.discount_amount

    def _recompute_booking_amounts(self):
        """
        Recalcular los montos de la reserva principal basándose en las líneas
        Solo se ejecuta cuando es necesario
        """
        self.ensure_one()

        # Solo recalcular si hay líneas y no viene del modal
        if self.booking_line_ids and not self.env.context.get("is_add_rooms_modal"):

            total_subtotal = 0
            total_taxed = 0

            for line in self.booking_line_ids:
                total_subtotal += line.subtotal_price or 0
                total_taxed += line.taxed_price or 0

            # El precio original se calcula automáticamente por el campo computado
            # No es necesario calcularlo manualmente aquí

            # Solo actualizar si hay cambios significativos
            if total_subtotal > 0 or total_taxed > 0:
                self.write(
                    {
                        "amount_untaxed": total_subtotal,
                        "total_amount": total_taxed,
                        "tax_amount": total_taxed - total_subtotal,
                    }
                )

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        """
        Sobrescribir para forzar el recálculo cuando se abre la vista
        """
        result = super().fields_view_get(view_id, view_type, toolbar, submenu)

        # Si es vista de formulario, forzar el recálculo de descuentos
        if view_type == "form" and self.env.context.get("active_id"):
            booking = self.browse(self.env.context["active_id"])
            if booking.exists():
                # El precio original y descuento se calculan automáticamente por campos computados
                # Solo actualizar la razón del descuento si es necesario
                if booking.discount_amount > 0 and not booking.discount_reason:
                    booking.discount_reason = "Descuento aplicado"

        return result

    def force_compute_original_price(self):
        """
        Método para forzar el recálculo del precio original
        Útil para corregir reservas existentes con precio original en 0
        """
        self.ensure_one()

        # Forzar recálculo
        self._compute_original_price()

        # Log del resultado
        _logger.info(
            "Booking %s: Forced original price computation. Result: %s (from %s lines)",
            self.id,
            self.original_price,
            len(self.booking_line_ids),
        )

        return self.original_price

    @api.model
    def fix_zero_original_prices(self):
        """
        Método utilitario para corregir reservas existentes con precio original en 0
        Se puede ejecutar desde código o desde un botón de administración
        """
        # Buscar reservas con precio original en 0 pero que tienen líneas de reserva
        problematic_bookings = self.search(
            [("original_price", "=", 0), ("booking_line_ids", "!=", False)]
        )

        fixed_count = 0
        for booking in problematic_bookings:
            old_price = booking.original_price
            booking.force_compute_original_price()

            if booking.original_price > 0:
                fixed_count += 1
                _logger.info(
                    "Fixed booking %s: original_price %s -> %s",
                    booking.id,
                    old_price,
                    booking.original_price,
                )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Corrección Completada"),
                "message": _("Se corrigieron %s reservas con precio original en 0.")
                % fixed_count,
                "type": "success",
            },
        }
