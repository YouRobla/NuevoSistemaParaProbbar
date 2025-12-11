# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class HotelBookingExtension(models.Model):
    _inherit = "hotel.booking"

    # --- CAMPOS PARA INGRESO MANUAL ---
    early_checkin_charge = fields.Monetary(
        string="Cargo por Early Check-in",
        currency_field="currency_id",
        help="Ingrese el monto a cobrar por el ingreso anticipado. Poner en 0 para anular.",
    )
    late_checkout_charge = fields.Monetary(
        string="Cargo por Late Check-out",
        currency_field="currency_id",
        help="Ingrese el monto a cobrar por la salida tardía. Poner en 0 para anular.",
    )

    # Campo computado para la suma de cargos adicionales
    additional_charges_total = fields.Monetary(
        string="Total Cargos Adicionales",
        currency_field="currency_id",
        compute="_compute_additional_charges_total",
        store=True,
        help="Suma total de cargos por Early Check-in y Late Check-out",
    )

    # --- CAMPOS DE CONFIGURACIÓN ---
    early_checkin_product_id = fields.Many2one(
        "product.product",
        string="Producto para Early Check-in",
        help="Producto de tipo servicio que se usará para registrar el cargo de Early Check-in.",
        default=lambda self: self.env.ref(
            "hotel_management_system_extension.product_service_early_checkin",
            raise_if_not_found=False,
        ),
    )
    late_checkout_product_id = fields.Many2one(
        "product.product",
        string="Producto para Late Check-out",
        help="Producto de tipo servicio que se usará para registrar el cargo de Late Check-out.",
        default=lambda self: self.env.ref(
            "hotel_management_system_extension.product_service_late_checkout",
            raise_if_not_found=False,
        ),
    )

    is_sync_services_allowed = fields.Boolean(
        string="Sincronización de Servicios Permitida",
        compute="_compute_available_actions",
        help="Indica si se puede sincronizar servicios (solo en reservas con cambio de habitación)",
    )

    # Campos para servicios adicionales manuales
    manual_service_description = fields.Char(
        string="Descripción del Servicio", help="Descripción del servicio adicional"
    )

    manual_service_amount = fields.Monetary(
        string="Costo del Servicio",
        currency_field="currency_id",
        help="Costo del servicio adicional que se sumará a la factura",
    )

    # Campo computed para mostrar solo servicios manuales
    manual_service_lines = fields.One2many(
        "hotel.booking.service.line",
        "booking_id",
        string="Servicios Manuales",
        compute="_compute_manual_service_lines",
        help="Servicios adicionales agregados manualmente",
    )

    @api.depends("hotel_service_lines")
    def _compute_manual_service_lines(self):
        """Filtrar solo los servicios manuales"""
        for record in self:
            # Buscar servicios que tengan el servicio genérico "Servicio Manual"
            manual_services = record.hotel_service_lines.filtered(
                lambda s: s.service_id and s.service_id.name == "Servicio Manual"
            )
            record.manual_service_lines = manual_services

    @api.onchange("manual_service_amount")
    def _onchange_manual_service_amount(self):
        """Hacer la descripción obligatoria solo si se ingresa un precio"""
        if self.manual_service_amount and self.manual_service_amount > 0:
            if not self.manual_service_description:
                return {
                    "warning": {
                        "title": _("Descripción Requerida"),
                        "message": _(
                            "Debe ingresar una descripción del servicio cuando se especifica un precio."
                        ),
                    }
                }
        return {}

    @api.depends(
        "early_checkin_charge", "late_checkout_charge", "hotel_service_lines.amount"
    )
    def _compute_additional_charges_total(self):
        """
        Calcular la suma total de cargos adicionales
        """
        for record in self:
            # Servicios especiales (early checkin, late checkout)
            special_charges = (record.early_checkin_charge or 0) + (
                record.late_checkout_charge or 0
            )

            # Servicios manuales agregados
            manual_services_total = sum(
                service.amount
                for service in record.hotel_service_lines
                if service.service_id and service.service_id.name == "Servicio Manual"
            )

            record.additional_charges_total = special_charges + manual_services_total

    @api.depends(
        "booking_line_ids.subtotal_price",
        "early_checkin_charge",
        "late_checkout_charge",
        "hotel_service_lines.amount",
    )
    def _compute_actual_amount(self):
        """
        Sobrescribir el método del módulo base para incluir cargos adicionales
        """
        for booking in self:
            total_tax_amount = 0
            total_amount = 0

            # Calcular totales de las líneas de reserva (lógica original)
            for line in booking.booking_line_ids:
                total_tax_amount += line.taxed_price
                total_amount += line.subtotal_price

            # Agregar cargos adicionales al total
            additional_charges = (booking.early_checkin_charge or 0) + (
                booking.late_checkout_charge or 0
            )

            # Agregar servicios manuales al total
            manual_services_total = sum(
                service.amount
                for service in booking.hotel_service_lines
                if service.service_id and service.service_id.name == "Servicio Manual"
            )

            # Actualizar campos
            booking.tax_amount = total_tax_amount - total_amount
            booking.amount_untaxed = (
                total_amount + additional_charges + manual_services_total
            )
            booking.total_amount = (
                total_tax_amount + additional_charges + manual_services_total
            )

            # Debug log para verificar cálculos
            _logger.info(
                f"Booking ID {booking.id}: Base amount={total_amount}, Additional charges={additional_charges}, Manual services={manual_services_total}, Final total={booking.total_amount}"
            )

    @api.onchange("early_checkin_charge")
    def _onchange_early_checkin_charge(self):
        """
        Manejar cambios en el cargo de Early Check-in
        """
        # Forzar el recálculo del total amount
        if self.early_checkin_charge or self.late_checkout_charge:
            self._compute_actual_amount()

        # Mostrar mensaje informativo si se agrega un cargo
        if self.early_checkin_charge and self.early_checkin_charge > 0:
            return {
                "warning": {
                    "title": _("Cargo por Early Check-in Agregado"),
                    "message": _(
                        "Se ha agregado un cargo de %s por Early Check-in. El total de la reserva se ha actualizado automáticamente."
                    )
                    % self.early_checkin_charge,
                }
            }

    @api.onchange("late_checkout_charge")
    def _onchange_late_checkout_charge(self):
        """
        Manejar cambios en el cargo de Late Check-out
        """
        # Forzar el recálculo del total amount
        if self.early_checkin_charge or self.late_checkout_charge:
            self._compute_actual_amount()

        # Mostrar mensaje informativo si se agrega un cargo
        if self.late_checkout_charge and self.late_checkout_charge > 0:
            return {
                "warning": {
                    "title": _("Cargo por Late Check-out Agregado"),
                    "message": _(
                        "Se ha agregado un cargo de %s por Late Check-out. El total de la reserva se ha actualizado automáticamente."
                    )
                    % self.late_checkout_charge,
                }
            }

    def action_add_extra_service(self):
        """
        Este método abre una ventana emergente (wizard/pop-up) para
        crear una nueva línea de servicio o costo extra.
        """
        self.ensure_one()

        # Verificar que hay líneas de reserva (booking_line_ids)
        if not self.booking_line_ids:
            raise UserError(
                _("Debe agregar habitaciones a la reserva antes de añadir servicios.")
            )

        # Usar la primera línea de reserva como booking_line_id por defecto
        default_booking_line_id = self.booking_line_ids[0].id

        return {
            "type": "ir.actions.act_window",
            "name": "Añadir Costo Extra",
            "res_model": "hotel.booking.service.line",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_booking_line_id": default_booking_line_id,
                "default_booking_id": self.id,
            },
            "view_id": self.env.ref(
                "hotel_management_system_extension.view_hotel_booking_service_line_form"
            ).id,
        }

    def action_add_manual_service(self):
        """Agregar servicio adicional manual a la reserva"""
        self.ensure_one()

        # Validar que si hay precio, debe haber descripción
        if self.manual_service_amount and self.manual_service_amount > 0:
            if not self.manual_service_description:
                raise UserError(
                    _(
                        "Debe ingresar una descripción del servicio cuando se especifica un precio."
                    )
                )

        # Validar que al menos uno de los campos esté lleno
        if not self.manual_service_description and not self.manual_service_amount:
            raise UserError(
                _(
                    "Debe ingresar al menos una descripción o un precio para el servicio adicional."
                )
            )

        if not self.booking_line_ids:
            raise UserError(
                _("Debe tener al menos una línea de reserva para agregar servicios.")
            )

        # Usar la primera línea de reserva como referencia
        booking_line = self.booking_line_ids[0]

        # Buscar o crear un servicio genérico para servicios manuales
        generic_service = self.env["hotel.service"].search(
            [("name", "=", "Servicio Manual"), ("service_type", "=", "paid")], limit=1
        )

        if not generic_service:
            # Crear un servicio genérico si no existe
            generic_service = self.env["hotel.service"].create(
                {
                    "name": "Servicio Manual",
                    "service_type": "paid",
                    "amount": 0.0,  # El monto se define en cada línea
                    "amount_type": "fixed",
                }
            )

        # Crear el servicio adicional
        service_vals = {
            "booking_id": self.id,
            "booking_line_id": booking_line.id,
            "service_id": generic_service.id,
            "amount": self.manual_service_amount or 0.0,  # Usar 0.0 si no hay precio
            "note": self.manual_service_description
            or "Servicio sin descripción",  # Usar descripción por defecto si no hay
            "state": "confirm",  # Confirmado automáticamente
        }

        # Crear la línea de servicio
        service_line = self.env["hotel.booking.service.line"].create(service_vals)

        # Debug: Verificar que el servicio se creó
        _logger.info(
            f"Servicio creado: ID={service_line.id}, Service ID={service_line.service_id.id}, Name={service_line.service_id.name}"
        )

        # Guardar los valores para el mensaje antes de limpiar
        description = self.manual_service_description
        amount = self.manual_service_amount

        # Limpiar los campos después de agregar el servicio
        self.write({"manual_service_description": False, "manual_service_amount": 0.0})

        # Forzar la actualización del campo computed
        self._compute_manual_service_lines()

        # Forzar el recálculo de totales para incluir el nuevo servicio
        self._compute_additional_charges_total()
        self._compute_actual_amount()

        # Debug: Verificar cuántos servicios manuales hay
        _logger.info(
            f"Servicios manuales encontrados: {len(self.manual_service_lines)}"
        )
        _logger.info(f"Total cargos adicionales: {self.additional_charges_total}")
        _logger.info(f"Total amount: {self.total_amount}")

        # Mensaje de confirmación
        self.message_post(
            body=f"Servicio adicional agregado: {description} - {self.currency_id.symbol}{amount}",
            message_type="notification",
        )

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def _get_or_create_service_product(self, service_name, description):
        """
        Obtener o crear un producto de servicio para facturación
        """
        # Buscar producto existente
        existing_product = self.env["product.product"].search(
            [
                ("name", "=", service_name),
                ("type", "=", "service"),
                ("sale_ok", "=", True),
            ],
            limit=1,
        )

        if existing_product:
            return existing_product

        # Crear nuevo producto si no existe
        try:
            new_product = self.env["product.product"].create(
                {
                    "name": service_name,
                    "type": "service",
                    "sale_ok": True,
                    "purchase_ok": False,
                    "list_price": 0.0,  # El precio se establece en la línea de venta
                    "description": description,
                    "categ_id": self._get_service_category().id,
                }
            )
            _logger.info("✅ Producto de servicio creado: %s", service_name)
            return new_product

        except Exception as e:
            _logger.error(
                "❌ Error creando producto de servicio %s: %s", service_name, str(e)
            )
            return None

    def _get_service_category(self):
        """
        Obtener o crear categoría para servicios de hotel
        """
        # Buscar categoría existente
        service_category = self.env["product.category"].search(
            [("name", "=", "Servicios de Hotel")], limit=1
        )

        if service_category:
            return service_category

        # Crear categoría si no existe
        try:
            service_category = self.env["product.category"].create(
                {
                    "name": "Servicios de Hotel",
                    "parent_id": False,
                }
            )
            _logger.info("✅ Categoría de servicios creada: Servicios de Hotel")
            return service_category

        except Exception as e:
            _logger.error("❌ Error creando categoría de servicios: %s", str(e))
            # Usar categoría por defecto
            return (
                self.env["product.category"].search([], limit=1)
                or self.env["product.category"]
            )

    def update_existing_sale_orders_with_services(self):
        """
        Actualizar órdenes de venta existentes agregando servicios faltantes
        Útil para reservas que ya tienen órdenes pero les faltan servicios
        """
        self.ensure_one()
        _logger.info("=== ACTUALIZANDO ÓRDENES EXISTENTES CON SERVICIOS FALTANTES ===")

        # Buscar todas las órdenes relacionadas
        all_orders = self.env["sale.order"].search(
            [("booking_id", "=", self.id), ("state", "in", ["draft", "sent", "sale"])]
        )

        if self.order_id and self.order_id not in all_orders:
            all_orders |= self.order_id

        if not all_orders:
            _logger.warning(
                "No se encontraron órdenes de venta para actualizar en reserva %s",
                self.id,
            )
            return 0

        total_services_added = 0

        for order in all_orders:
            _logger.info("Actualizando orden %s", order.name)

            # Verificar qué servicios ya existen en la orden
            existing_service_names = set(order.order_line.mapped("name"))

            services_to_add = []

            # Early Check-in
            if (
                self.early_checkin_charge
                and self.early_checkin_charge > 0
                and "Early Check-in" not in existing_service_names
            ):
                services_to_add.append(
                    {
                        "name": "Early Check-in",
                        "amount": self.early_checkin_charge,
                        "description": "Servicio de ingreso anticipado",
                    }
                )

            # Late Check-out
            if (
                self.late_checkout_charge
                and self.late_checkout_charge > 0
                and "Late Check-out" not in existing_service_names
            ):
                services_to_add.append(
                    {
                        "name": "Late Check-out",
                        "amount": self.late_checkout_charge,
                        "description": "Servicio de salida tardía",
                    }
                )

            # Servicios manuales
            manual_services = self.hotel_service_lines.filtered(
                lambda s: s.service_id
                and s.service_id.name == "Servicio Manual"
                and s.amount > 0
            )

            for service_line in manual_services:
                service_name = service_line.note or "Servicio Manual"
                if service_name not in existing_service_names:
                    services_to_add.append(
                        {
                            "name": service_name,
                            "amount": service_line.amount,
                            "description": service_line.note or "Servicio adicional",
                        }
                    )

            # Agregar servicios faltantes
            for service_info in services_to_add:
                service_product = self._get_or_create_service_product(
                    service_info["name"], service_info["description"]
                )

                if service_product:
                    try:
                        self.env["sale.order.line"].create(
                            {
                                "order_id": order.id,
                                "product_id": service_product.id,
                                "name": service_info["name"],
                                "product_uom_qty": 1,
                                "price_unit": service_info["amount"],
                                "tax_id": [(6, 0, service_product.taxes_id.ids)],
                            }
                        )
                        total_services_added += 1
                        _logger.info(
                            "✅ Servicio agregado a orden %s: %s - %s",
                            order.name,
                            service_info["name"],
                            service_info["amount"],
                        )
                    except Exception as e:
                        _logger.error(
                            "❌ Error agregando servicio %s a orden %s: %s",
                            service_info["name"],
                            order.name,
                            str(e),
                        )

        if total_services_added > 0:
            self.message_post(
                body=_(
                    "✅ %s servicios adicionales agregados a órdenes de venta existentes"
                )
                % total_services_added,
                subject=_("Órdenes Actualizadas con Servicios"),
            )

        _logger.info(
            "=== ACTUALIZACIÓN COMPLETADA: %s servicios agregados ===",
            total_services_added,
        )
        return total_services_added

    def action_sync_services_to_sale_orders(self):
        """
        Acción del botón para sincronizar servicios con órdenes de venta
        """
        self.ensure_one()

        try:
            services_added = self.update_existing_sale_orders_with_services()

            if services_added > 0:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Sincronización Exitosa"),
                        "message": _(
                            "✅ %s servicios adicionales sincronizados con las órdenes de venta"
                        )
                        % services_added,
                        "type": "success",
                        "sticky": True,
                    },
                }
            else:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Sincronización Completada"),
                        "message": _(
                            "ℹ️ Todos los servicios ya están sincronizados con las órdenes de venta"
                        ),
                        "type": "info",
                        "sticky": False,
                    },
                }

        except Exception as e:
            _logger.error(
                "Error en sincronización de servicios para reserva %s: %s",
                self.id,
                str(e),
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error en Sincronización"),
                    "message": _("❌ Error al sincronizar servicios: %s") % str(e),
                    "type": "danger",
                    "sticky": False,
                },
            }

    def _process_checkout_services(self):
        """Procesar servicios durante el checkout"""
        try:
            # Replicar la funcionalidad del método base si existe
            if hasattr(super(), "manage_alloted_services"):
                res = self.manage_alloted_services()
                if res:
                    return res

            # Configuración de facturación automática
            auto_invoice = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.auto_invoice_gen")
            )
            if auto_invoice and hasattr(self, "create_invoice"):
                self.create_invoice()

            # Configuración de feedback
            feedback_config = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.feedback_config")
            )
            if feedback_config == "at_checkout" and hasattr(self, "send_feedback_btn"):
                self.send_feedback_btn()

            # Configuración de facturación de agente
            auto_bill = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.auto_bill_gen")
            )
            if (
                auto_bill
                and hasattr(self, "via_agent")
                and self.via_agent
                and hasattr(self, "create_agent_bill")
            ):
                self.create_agent_bill()

            # Configuración de housekeeping
            hk_mode = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.housekeeping_config")
            )
            if hk_mode in ["at_checkout", "both"] and hasattr(
                self, "create_housekeeping"
            ):
                self.create_housekeeping()

            # Configuración de email de check-out
            email_on_checkout = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("hotel_management_system.send_on_checkout")
            )
            if email_on_checkout and hasattr(self, "send_checkout_email"):
                self.send_checkout_email()

        except Exception as e:
            _logger.warning("Error processing checkout services: %s", str(e))

    def _release_rooms(self):
        """Liberar habitaciones asignadas"""
        for line in self.booking_line_ids:
            if hasattr(line.product_id, "room_status"):
                line.product_id.room_status = "available"

    def _apply_no_show_policy(self):
        """Aplicar política de no show"""
        # Implementar lógica de penalización por no show
        # Esto dependerá de las políticas específicas del hotel
        pass
