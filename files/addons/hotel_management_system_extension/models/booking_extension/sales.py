# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class HotelBookingExtension(models.Model):
    _inherit = "hotel.booking"

    def _create_sale_order_for_booking(self):
        """
        Crear una orden de venta automática para la reserva
        """
        try:
            _logger.info(
                "=== INICIANDO CREACIÓN DE ORDEN DE VENTA PARA RESERVA %s ===", self.id
            )

            # Validar que la reserva tenga los datos mínimos necesarios
            _logger.info("Validando datos básicos de reserva %s", self.id)
            _logger.info(
                "Partner: %s, Check-in: %s, Check-out: %s",
                self.partner_id.name if self.partner_id else "None",
                self.check_in,
                self.check_out,
            )

            if not self.partner_id:
                raise ValidationError(_("La reserva debe tener un cliente asignado."))

            if not self.check_in or not self.check_out:
                raise ValidationError(
                    _("La reserva debe tener fechas de check-in y check-out válidas.")
                )

            if not self.booking_line_ids:
                raise ValidationError(
                    _("La reserva debe tener al menos una habitación asignada.")
                )

            _logger.info(
                "Reserva %s tiene %s líneas de habitación",
                self.id,
                len(self.booking_line_ids),
            )
            for line in self.booking_line_ids:
                _logger.info(
                    "Línea: producto=%s, precio=%s, descuento=%s",
                    line.product_id.name,
                    line.price,
                    line.discount,
                )

            # Calcular los días de reserva si no están calculados
            if (
                not hasattr(self, "booking_days")
                or not self.booking_days
                or self.booking_days <= 0
            ):
                try:
                    self._compute_booking_days()
                except Exception as compute_error:
                    _logger.warning(
                        "Error calculando booking_days, usando cálculo manual: %s",
                        str(compute_error),
                    )
                    # Cálculo manual como fallback (permitir fracciones para reservas de pocas horas)
                    if self.check_in and self.check_out:
                        days_diff = (self.check_out.date() - self.check_in.date()).days

                        # Si es el mismo día o diferencia pequeña, calcular en horas
                        if days_diff == 0:
                            # Mismo día: calcular duración en horas
                            if isinstance(self.check_in, datetime) and isinstance(
                                self.check_out, datetime
                            ):
                                time_diff = self.check_out - self.check_in
                                hours = time_diff.total_seconds() / 3600.0
                                # Convertir horas a fracción de día
                                self.booking_days = max(
                                    0.01, hours / 24.0
                                )  # Mínimo 0.01 días para visualización
                            else:
                                self.booking_days = 0.5  # Medio día por defecto
                        else:
                            # Múltiples días: calcular con precisión de horas
                            if isinstance(self.check_in, datetime) and isinstance(
                                self.check_out, datetime
                            ):
                                time_diff = self.check_out - self.check_in
                                total_hours = time_diff.total_seconds() / 3600.0
                                self.booking_days = max(
                                    0.01, total_hours / 24.0
                                )  # Convertir a días fraccionales
                            else:
                                self.booking_days = max(
                                    0.01, days_diff
                                )  # Mínimo 0.01 días
                    else:
                        self.booking_days = 0.5  # Medio día por defecto

            _logger.info("Días de reserva calculados: %s", self.booking_days)

            # Preparar los datos de la orden de venta (exactamente como el módulo padre)
            order_vals = {
                "state": "sale",  # IMPORTANTE: Crear directamente en estado 'sale' como el módulo padre
                "hotel_check_in": self.check_in,
                "booking_id": self.id,
                "partner_id": self.partner_id.id,
                "hotel_check_out": self.check_out,
                "pricelist_id": self.pricelist_id.id if self.pricelist_id else False,
                "hotel_id": self.hotel_id.id if self.hotel_id else False,
                "booking_count": 1,
            }

            # Crear la orden de venta
            _logger.info("Creando orden de venta con datos: %s", order_vals)
            try:
                sale_order = self.env["sale.order"].create(order_vals)
                _logger.info(
                    "Orden de venta creada exitosamente: ID=%s, Name=%s",
                    sale_order.id,
                    sale_order.name,
                )
            except Exception as e:
                _logger.error("Error al crear orden de venta: %s", str(e))
                return False

            if not sale_order:
                _logger.error("Error: No se pudo crear la orden de venta")
                return False

            # Procesar cada línea de reserva para crear líneas de orden de venta (exactamente como el módulo padre)
            for line in self.booking_line_ids:
                _logger.info("Procesando línea de reserva: %s", line.product_id.name)

                # Preparar datos exactamente como el módulo padre
                line_data = {
                    "tax_id": line.tax_ids,
                    "order_id": sale_order.id,
                    "product_id": line.product_id.id,
                    "product_uom_qty": self.booking_days,
                    "price_unit": line.price,
                    "guest_info_ids": (
                        line.guest_info_ids
                        if hasattr(line, "guest_info_ids")
                        else False
                    ),
                    "discount": line.discount,
                }
                _logger.info("Datos para crear línea de orden: %s", line_data)

                # Crear línea exactamente como el módulo padre
                try:
                    sale_order_line = self.env["sale.order.line"].create(line_data)
                    line.sale_order_line_id = sale_order_line.id
                    _logger.info(
                        "Línea de orden creada exitosamente: ID=%s, producto=%s, cantidad=%s",
                        sale_order_line.id,
                        sale_order_line.product_id.name,
                        sale_order_line.product_uom_qty,
                    )
                except Exception as line_error:
                    _logger.error("ERROR creando línea de orden: %s", str(line_error))
                    _logger.error("Datos que causaron el error: %s", line_data)
                    raise

            # NUEVO: Agregar servicios adicionales a la orden de venta
            if hasattr(self, "_add_additional_services_to_sale_order"):
                self._add_additional_services_to_sale_order(sale_order)

            # Verificar que las líneas se crearon correctamente
            _logger.info(
                "Orden de venta %s tiene %s líneas después de la creación",
                sale_order.id,
                len(sale_order.order_line),
            )

            # IMPORTANTE: La orden se crea directamente en estado 'sale' como el módulo padre
            # No es necesario llamar action_confirm() porque ya está confirmada

            # Actualizar la reserva con la orden de venta creada
            self.write({"order_id": sale_order.id})

            # Crear mensaje de seguimiento
            booking_days = getattr(
                self, "booking_days", 1
            )  # Usar 1 como valor por defecto si no existe booking_days
            self.message_post(
                body=_(
                    "Orden de venta creada y confirmada automáticamente con %s días de reserva."
                )
                % booking_days,
                subject=_("Orden de Venta Creada"),
            )

            return sale_order

        except Exception as e:
            _logger.error(
                "Error creating sale order for booking %s: %s", self.id, str(e)
            )
            # Crear mensaje de error más detallado
            self.message_post(
                body=_("Error al crear orden de venta: %s") % str(e),
                subject=_("Error en Creación de Orden de Venta"),
                message_type="comment",
            )
            return False

    def _add_additional_services_to_sale_order(self, sale_order):
        """
        Agregar servicios adicionales (early check-in, late check-out, servicios manuales)
        a la orden de venta para que se facturen correctamente
        """
        self.ensure_one()
        _logger.info(
            "=== AGREGANDO SERVICIOS ADICIONALES A ORDEN DE VENTA %s ===",
            sale_order.name,
        )

        services_added = 0

        # 1. EARLY CHECK-IN SERVICE
        if self.early_checkin_charge and self.early_checkin_charge > 0:
            early_checkin_product = self._get_or_create_service_product(
                "Early Check-in", "Servicio de ingreso anticipado"
            )

            if early_checkin_product:
                try:
                    self.env["sale.order.line"].create(
                        {
                            "order_id": sale_order.id,
                            "product_id": early_checkin_product.id,
                            "name": "Early Check-in",
                            "product_uom_qty": 1,
                            "price_unit": self.early_checkin_charge,
                            "tax_id": [(6, 0, early_checkin_product.taxes_id.ids)],
                        }
                    )
                    services_added += 1
                    _logger.info(
                        "✅ Early Check-in agregado: %s", self.early_checkin_charge
                    )
                except Exception as e:
                    _logger.error("❌ Error agregando Early Check-in: %s", str(e))

        # 2. LATE CHECK-OUT SERVICE
        if self.late_checkout_charge and self.late_checkout_charge > 0:
            late_checkout_product = self._get_or_create_service_product(
                "Late Check-out", "Servicio de salida tardía"
            )

            if late_checkout_product:
                try:
                    self.env["sale.order.line"].create(
                        {
                            "order_id": sale_order.id,
                            "product_id": late_checkout_product.id,
                            "name": "Late Check-out",
                            "product_uom_qty": 1,
                            "price_unit": self.late_checkout_charge,
                            "tax_id": [(6, 0, late_checkout_product.taxes_id.ids)],
                        }
                    )
                    services_added += 1
                    _logger.info(
                        "✅ Late Check-out agregado: %s", self.late_checkout_charge
                    )
                except Exception as e:
                    _logger.error("❌ Error agregando Late Check-out: %s", str(e))

        # 3. SERVICIOS MANUALES
        manual_services = self.hotel_service_lines.filtered(
            lambda s: s.service_id
            and s.service_id.name == "Servicio Manual"
            and s.amount > 0
        )

        for service_line in manual_services:
            manual_service_product = self._get_or_create_service_product(
                "Servicio Manual", service_line.note or "Servicio adicional"
            )

            if manual_service_product:
                try:
                    self.env["sale.order.line"].create(
                        {
                            "order_id": sale_order.id,
                            "product_id": manual_service_product.id,
                            "name": service_line.note or "Servicio Manual",
                            "product_uom_qty": 1,
                            "price_unit": service_line.amount,
                            "tax_id": [(6, 0, manual_service_product.taxes_id.ids)],
                        }
                    )
                    services_added += 1
                    _logger.info(
                        "✅ Servicio manual agregado: %s - %s",
                        service_line.note,
                        service_line.amount,
                    )
                except Exception as e:
                    _logger.error("❌ Error agregando servicio manual: %s", str(e))

        # 4. OTROS SERVICIOS DEL HOTEL (si existen)
        other_services = self.hotel_service_lines.filtered(
            lambda s: s.service_id
            and s.service_id.name != "Servicio Manual"
            and s.amount > 0
        )

        for service_line in other_services:
            # Intentar usar el producto del servicio directamente si es posible
            service_product = None

            # Si el servicio tiene un producto asociado, usarlo
            if (
                hasattr(service_line.service_id, "product_id")
                and service_line.service_id.product_id
            ):
                service_product = service_line.service_id.product_id
            else:
                # Crear o buscar producto para este servicio
                service_product = self._get_or_create_service_product(
                    service_line.service_id.name,
                    service_line.note or service_line.service_id.name,
                )

            if service_product:
                try:
                    self.env["sale.order.line"].create(
                        {
                            "order_id": sale_order.id,
                            "product_id": service_product.id,
                            "name": service_line.note or service_line.service_id.name,
                            "product_uom_qty": 1,
                            "price_unit": service_line.amount,
                            "tax_id": [(6, 0, service_product.taxes_id.ids)],
                        }
                    )
                    services_added += 1
                    _logger.info(
                        "✅ Servicio hotel agregado: %s - %s",
                        service_line.service_id.name,
                        service_line.amount,
                    )
                except Exception as e:
                    _logger.error("❌ Error agregando servicio hotel: %s", str(e))

        _logger.info(
            "=== SERVICIOS ADICIONALES COMPLETADOS: %s servicios agregados ===",
            services_added,
        )

        # Actualizar mensaje en el chatter
        if services_added > 0:
            self.message_post(
                body=_(
                    "✅ %s servicios adicionales agregados automáticamente a la orden de venta %s"
                )
                % (services_added, sale_order.name),
                subject=_("Servicios Adicionales Agregados"),
            )

        return services_added

    def action_register_payment(self):
        """
        Sobrescribir el método de pago por adelantado para manejar reservas sin orden de venta
        """
        self.ensure_one()

        # Si no hay orden de venta, crear una automáticamente
        if not self.order_id:
            # Crear una orden de venta básica para la reserva
            sale_order = self._create_sale_order_for_booking()
            if not sale_order:
                raise UserError(
                    _("No se pudo crear la orden de venta para el pago por adelantado.")
                )

        # Llamar al método original del módulo base
        return super().action_register_payment()

    def action_view_compute_bill(self):
        """
        Sobrescribir para funcionar exactamente como el módulo padre
        NO crear órdenes de venta automáticamente
        """
        self.ensure_one()

        # Validar que el estado sea correcto para Print Bill
        # Estados válidos: checkin, checkout, cleaning_needed, room_ready, allot
        valid_states = ["checkin", "checkout", "cleaning_needed", "room_ready", "allot"]
        if self.status_bar not in valid_states:
            # Mapear estados del módulo hijo a mensajes claros
            state_messages = {
                "initial": "Reserva en borrador. Complete la configuración primero.",
                "confirmed": "Reserva confirmada. Realice check-in primero.",
                "no_show": "Reserva marcada como No Show. No se puede facturar.",
                "cancelled": "Reserva cancelada. No se puede facturar.",
            }

            message = state_messages.get(
                self.status_bar,
                f"El botón Print Bill no está disponible en el estado '{self.status_bar}'",
            )

            # Verificar si existe wk.wizard.message
            if self.env["wk.wizard.message"].sudo()._name:
                return self.env["wk.wizard.message"].genrated_message(
                    f"{message} El botón Print Bill solo está disponible después de confirmar la reserva.",
                    name="Estado Incorrecto",
                )
            else:
                raise UserError(
                    f"{message} El botón Print Bill solo está disponible después de confirmar la reserva."
                )

        # Validaciones básicas antes de proceder
        if not self.check_in or not self.check_out:
            message = "Por favor complete las fechas de Check-in y Check-out antes de generar la factura."
            if self.env["wk.wizard.message"].sudo()._name:
                return self.env["wk.wizard.message"].genrated_message(
                    message, name="Error de Validación"
                )
            else:
                raise UserError(message)

        if not self.booking_line_ids:
            message = "No hay habitaciones asignadas. Agregue habitaciones antes de generar la factura."
            if self.env["wk.wizard.message"].sudo()._name:
                return self.env["wk.wizard.message"].genrated_message(
                    message, name="Error de Validación"
                )
            else:
                raise UserError(message)

        # IMPORTANTE: NO crear órdenes de venta automáticamente
        # Solo buscar las existentes como hace el módulo padre

        # Buscar órdenes de venta relacionadas (exactamente como el módulo padre)
        order_ids = self.env["sale.order"].search(
            [("booking_id", "=", self.id), ("state", "=", "sale")]
        )

        # Combinar orden principal con órdenes adicionales (exactamente como el módulo padre)
        all_orders = (self.order_id | order_ids) if self.order_id else order_ids

        # Si no hay órdenes, intentar crear una automáticamente (como respaldo)
        if not all_orders:
            try:
                _logger.info(
                    "No se encontraron órdenes de venta para reserva %s, intentando crear una automáticamente",
                    self.id,
                )
                sale_order = self._create_sale_order_for_booking()
                if sale_order:
                    # Buscar nuevamente las órdenes
                    order_ids = self.env["sale.order"].search(
                        [("booking_id", "=", self.id), ("state", "=", "sale")]
                    )
                    all_orders = (
                        (self.order_id | order_ids) if self.order_id else order_ids
                    )

                    if all_orders:
                        _logger.info(
                            "Orden de venta creada automáticamente %s para reserva %s",
                            sale_order.name,
                            self.id,
                        )
                    else:
                        message = (
                            "No se pudieron crear órdenes de venta automáticamente. "
                            "Verifique que la reserva tenga todos los datos necesarios."
                        )
                        if self.env["wk.wizard.message"].sudo()._name:
                            return self.env["wk.wizard.message"].genrated_message(
                                message, name="Error en Creación Automática"
                            )
                        else:
                            raise UserError(message)
                else:
                    message = (
                        "No se pudieron crear órdenes de venta automáticamente. "
                        "Verifique que la reserva tenga todos los datos necesarios."
                    )
                    if self.env["wk.wizard.message"].sudo()._name:
                        return self.env["wk.wizard.message"].genrated_message(
                            message, name="Error en Creación Automática"
                        )
                    else:
                        raise UserError(message)
            except Exception as e:
                _logger.error(
                    "Error creando orden de venta automática para Print Bill en reserva %s: %s",
                    self.id,
                    str(e),
                )
                message = (
                    f"Error al crear orden de venta automáticamente: {str(e)}. "
                    "Verifique que la reserva tenga todos los datos necesarios."
                )
                if self.env["wk.wizard.message"].sudo()._name:
                    return self.env["wk.wizard.message"].genrated_message(
                        message, name="Error en Creación Automática"
                    )
                else:
                    raise UserError(message)

        # Retornar exactamente como el módulo padre
        return {
            "name": _("Booking Bill"),
            "type": "ir.actions.act_window",
            "res_model": "booking.bill",
            "view_id": self.env.ref("hotel_management_system.view_compute_bill").id,
            "view_mode": "form",
            "target": "new",
            "context": {"order_list": all_orders.ids},
        }

    def filter_booking_based_on_date(self, check_in, check_out):
        """
        Sobrescribir para evitar la validación problemática cuando estamos
        en contexto de Print Bill
        """
        # Si estamos en contexto de Print Bill, hacer una validación más permisiva
        if self.env.context.get("is_print_bill_context"):
            # Solo validar que las fechas existan, pero no hacer la validación estricta
            if not (check_in and check_out):
                return self.env["hotel.booking"]

            # Para Print Bill, solo verificar que no haya conflictos reales
            # pero permitir que la reserva actual pase la validación
            check_in_date = check_in.date() if hasattr(check_in, "date") else check_in
            check_out_date = (
                check_out.date() if hasattr(check_out, "date") else check_out
            )

            return self.filtered(
                lambda r: (
                    r.status_bar not in ("cancel", "checkout")
                    and r.check_in
                    and r.check_out
                    and
                    # Solo hay conflicto si las fechas se solapan realmente
                    not (
                        r.check_out.date() <= check_in_date
                        or r.check_in.date() >= check_out_date
                    )
                )
            )

        # Si no es contexto de Print Bill, usar la lógica original del módulo padre
        return super().filter_booking_based_on_date(check_in, check_out)
