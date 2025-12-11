# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class HotelBookingExtension(models.Model):
    _inherit = "hotel.booking"

    # Heredar campos del módulo padre para compatibilidad con Create Invoice
    is_show_create_invoice_btn = fields.Boolean(
        "Is show Create Button",
        compute="_compute_show_btn",
        help="Campo heredado del módulo padre para controlar visibilidad del botón Create Invoice.",
    )

    # Campo para motivo del viaje
    motivo_viaje = fields.Char(
        string="Motivo del Viaje",
        help="Indique el motivo del viaje (Vacaciones, Negocios, etc)",
    )

    # Campos para vincular reservas (cambio de habitación)
    connected_booking_id = fields.Many2one(
        "hotel.booking",
        string="Reserva Vinculada",
        readonly=True,
        help="Reserva vinculada (por ejemplo, la nueva reserva tras un cambio de habitación)",
    )

    split_from_booking_id = fields.Many2one(
        "hotel.booking",
        string="Continuación de Reserva",
        readonly=True,
        help="Reserva original de la que se originó este cambio de habitación",
    )

    is_room_change_origin = fields.Boolean(
        string="Es Origen de Cambio",
        default=False,
        help="Indica si esta reserva es el origen de un cambio de habitación",
    )

    is_room_change_destination = fields.Boolean(
        string="Es Destino de Cambio",
        default=False,
        help="Indica si esta reserva es el destino de un cambio de habitación",
    )

    # --- SOBRESCRIBIR CAMPOS PRINCIPALES PARA SOPORTE DE HORAS ---

    # Redefinir booking_days como Float para aceptar fracciones de día (horas)
    booking_days = fields.Float(
        string="Days Book For",
        compute="_compute_booking_days",
        store=True,
        copy=False,
        tracking=True,
        digits=(16, 4),  # Precisión para horas (ej: 0.0416 es 1 hora)
        help="Días de reserva. Puede incluir fracciones para reservas por horas.",
    )

    @api.depends("check_out", "check_in")
    def _compute_booking_days(self):
        """
        Sobrescribir cálculo de días para soportar horas (fracciones de día).
        """
        for rec in self:
            if rec.check_in and rec.check_out:
                # Calcular diferencia usando datetimes completos
                diff = rec.check_out - rec.check_in
                # Convertir a líneas flotantes de días
                # total_seconds / 3600 = horas -> / 24 = días
                days = diff.total_seconds() / 86400.0
                rec.booking_days = max(0.0, days)
            else:
                rec.booking_days = 0.0

    def filter_booking_based_on_date(self, check_in, check_out):
        """
        Sobrescribir filtro de reservas para usar comparación precisa de fecha Y HORA.
        Esto permite reservas por horas en el mismo día.
        """
        if not (check_in and check_out):
            raise ValidationError(
                _("Please fill the Check in and Check out Details !!")
            )

        # Asegurar que son datetimes
        if isinstance(check_in, str):
            check_in = fields.Datetime.from_string(check_in)
        if isinstance(check_out, str):
            check_out = fields.Datetime.from_string(check_out)

        # Filtrar reservas que se traslapan con el rango dado
        # Logica: Hay traslape si (StartA < EndB) y (EndA > StartB)
        return self.filtered(
            lambda r: (
                r.status_bar not in ("cancel", "checkout")
                and r.check_in < check_out
                and r.check_out > check_in
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir create para logging de fechas y debugging del desfase +1 día
        Mejorado para Odoo 17
        """
        # Log de debugging para fechas
        for vals in vals_list:
            if "check_in" in vals or "check_out" in vals:
                _logger.info(
                    "DEBUG - Creando reserva con fechas: check_in=%s, check_out=%s, "
                    "check_in_type=%s, check_out_type=%s",
                    vals.get("check_in"),
                    vals.get("check_out"),
                    type(vals.get("check_in")).__name__,
                    type(vals.get("check_out")).__name__,
                )

        # Crear la reserva
        result = super().create(vals_list)

        # Log adicional después de la creación
        for record in result:
            _logger.info(
                "DEBUG - Reserva creada ID=%s: check_in=%s, check_out=%s, "
                "check_in_date=%s, check_out_date=%s",
                record.id,
                record.check_in,
                record.check_out,
                record.check_in.date() if record.check_in else None,
                record.check_out.date() if record.check_out else None,
            )

        return result

    def _compute_show_btn(self):
        """
        Método heredado del módulo padre para controlar la visibilidad del botón Create Invoice.
        Mantiene la misma lógica: si auto_invoice_gen está activado, oculta el botón manual.
        """
        is_show_create_invoice_btn = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hotel_management_system.auto_invoice_gen")
        )
        for rec in self:
            rec.is_show_create_invoice_btn = is_show_create_invoice_btn

    def copy_all_data_to_booking(self, target_booking):
        """
        Método auxiliar para copiar toda la información relevante a otra reserva
        Útil para cambios de habitación y transferencias
        """
        _logger.info("=== COPIANDO DATOS COMPLETOS ENTRE RESERVAS ===")

        # 1. Copiar servicios manuales
        services_copied = 0
        for service_line in self.hotel_service_lines:
            if (
                service_line.service_id
                and service_line.service_id.name == "Servicio Manual"
            ):
                new_service_vals = {
                    "booking_id": target_booking.id,
                    "service_id": service_line.service_id.id,
                    "service_type": service_line.service_type,
                    "amount": service_line.amount,
                    "note": service_line.note,
                    "state": "draft",
                }
                self.env["hotel.booking.service.line"].create(new_service_vals)
                services_copied += 1

        # 2. Transferir órdenes de venta
        sale_orders = self.env["sale.order"].search([("booking_id", "=", self.id)])
        orders_transferred = 0
        if sale_orders:
            sale_orders.write({"booking_id": target_booking.id})
            orders_transferred = len(sale_orders)

        _logger.info(
            "Datos copiados: %d servicios, %d órdenes transferidas",
            services_copied,
            orders_transferred,
        )

        # 3. Mensajes informativos
        self.message_post(
            body=_(
                "✅ Datos transferidos a reserva %s: %d servicios manuales, %d órdenes de venta."
            )
            % (
                target_booking.sequence_id or f"#{target_booking.id}",
                services_copied,
                orders_transferred,
            ),
            subject=_("Transferencia de Datos Completada"),
        )

        target_booking.message_post(
            body=_(
                "📥 Datos recibidos desde reserva %s: %d servicios manuales, %d órdenes de venta."
            )
            % (self.sequence_id or f"#{self.id}", services_copied, orders_transferred),
            subject=_("Datos Recibidos"),
        )

    def action_view_original_booking(self):
        """
        Acción para navegar a la reserva original de la que se originó este cambio de habitación
        """
        if not self.split_from_booking_id:
            return

        return {
            "type": "ir.actions.act_window",
            "name": _("Reserva Original"),
            "res_model": "hotel.booking",
            "res_id": self.split_from_booking_id.id,
            "view_mode": "form",
            "target": "current",
            "context": self.env.context,
        }
