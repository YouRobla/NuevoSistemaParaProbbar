# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from ..api_auth import validate_api_key
from .utils import handle_api_errors, TERMINAL_STATUSES

_logger = logging.getLogger(__name__)


class OperationEndpoints:

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>/habitaciones",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def add_rooms_to_reserva(self, reserva_id, **kw):
        """Agregar habitaciones a una reserva existente"""
        booking = request.env["hotel.booking"].browse(reserva_id)
        if not booking.exists():
            return self._prepare_response(
                {
                    "success": False,
                    "error": f"La reserva con ID {reserva_id} no existe",
                },
                status=404,
            )

        self._check_access_rule(booking, "read")
        self._check_access_rights("hotel.booking", "write")
        self._check_access_rule(booking, "write")
        self._check_access_rights("hotel.booking.line", "create")

        if booking.status_bar in TERMINAL_STATUSES:
            return self._prepare_response(
                {
                    "success": False,
                    "error": f'No se pueden agregar habitaciones a una reserva en estado "{booking.status_bar}"',
                },
                status=400,
            )

        data = self._parse_json_data()
        if not data.get("rooms"):
            raise ValueError("Debe especificar al menos una habitación")

        self._validate_rooms_data(data["rooms"])
        self._create_booking_lines(booking.id, data["rooms"])

        _logger.info(
            "Se agregaron %s habitaciones a la reserva %s",
            len(data["rooms"]),
            reserva_id,
        )

        return self._prepare_response(
            {
                "success": True,
                "message": f'{len(data["rooms"])} habitación(es) agregada(s) exitosamente',
                "data": self._build_booking_data(booking),
            }
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>/estado",
        auth="public",
        type="http",
        methods=["PUT"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def change_reserva_status(self, reserva_id, **kw):
        """Cambiar el estado de una reserva"""
        booking = request.env["hotel.booking"].browse(reserva_id)
        if not booking.exists():
            return self._prepare_response(
                {
                    "success": False,
                    "error": f"La reserva con ID {reserva_id} no existe",
                },
                status=404,
            )

        self._check_access_rule(booking, "read")
        self._check_access_rights("hotel.booking", "write")
        self._check_access_rule(booking, "write")

        data = self._parse_request_data()
        if not data.get("status_bar"):
            raise ValueError("Debe especificar el nuevo estado (status_bar)")

        new_status = data["status_bar"]
        if new_status in ["checked_in", "check_in"]:
            new_status = "checkin"

        self._validate_booking_status(new_status)
        self._validate_status_transition(booking.status_bar, new_status)

        # Capturar horas actuales o del payload antes de que el cambio de estado las resetee
        # Aseguramos conversion a int para evitar errores en datetime.time combinados con float
        try:
            cur_in_h = int(booking.check_in_hour) if booking.check_in and booking.check_in_hour else 0
            cur_in_m = int(booking.check_in_minute) if booking.check_in and booking.check_in_minute else 0
            cur_out_h = int(booking.check_out_hour) if booking.check_out and booking.check_out_hour else 0
            cur_out_m = int(booking.check_out_minute) if booking.check_out and booking.check_out_minute else 0
        except Exception:
            _logger.warning("Error getting current hours from booking %s", reserva_id)
            cur_in_h, cur_in_m, cur_out_h, cur_out_m = 15, 0, 12, 0 # Fallback

        # Prioridad: Payload > Base de datos
        def _parse_int(val, default):
            try:
                parsed = int(val) if val is not None else default
                return parsed
            except (ValueError, TypeError):
                return default

        target_in_h = _parse_int(data.get("check_in_hour"), cur_in_h)
        target_in_m = _parse_int(data.get("check_in_minute"), cur_in_m)
        target_out_h = _parse_int(data.get("check_out_hour"), cur_out_h)
        target_out_m = _parse_int(data.get("check_out_minute"), cur_out_m)

        # Eliminar campos de hora del payload para que no fallen en el write/action
        # ya que estos campos son computados o no existen directamente para escritura simple en algunos contextos
        # y nosotros los manejamos manualmente al final
        # Eliminar campos de hora del payload para que no fallen en el write/action
        # ya que estos campos son computados o no existen directamente para escritura simple en algunos contextos
        # y nosotros los manejamos manualmente al final
        for field_to_pop in ['check_in_hour', 'check_in_minute', 'check_out_hour', 'check_out_minute']:
            data.pop(field_to_pop, None)

        old_status = booking.status_bar
        final_status = new_status
        triggered_action = False

        if new_status in ["confirmed", "confirm"] and hasattr(
            booking, "action_confirm_booking"
        ):
            try:
                booking.action_confirm_booking()
                triggered_action = True
                final_status = booking.status_bar
            except Exception as exc:
                _logger.error(
                    "Error ejecutando action_confirm_booking en reserva %s: %s",
                    reserva_id,
                    str(exc),
                )
                raise ValueError(f"No se pudo confirmar la reserva: {str(exc)}")
        else:
            booking.write({"status_bar": new_status})

        # Restaurar/Actualizar horas después del cambio de estado (que podría haberlas reseteado a 12:00)
        time_updates = {}
        
        # Actualizar Check-in
        if booking.check_in:
            # Usar la fecha que quedó después del cambio de estado (pero corregir la hora)
            # Nota: Odoo devuelve datetime, convertimos a date para combinar
            check_in_obj = booking.check_in
            if isinstance(check_in_obj, str):
                check_in_obj = fields.Datetime.from_string(check_in_obj)
            
            new_check_in = datetime.combine(
                check_in_obj.date(),
                time(hour=target_in_h, minute=target_in_m)
            )
            time_updates['check_in'] = fields.Datetime.to_string(new_check_in)

        # Actualizar Check-out
        if booking.check_out:
            check_out_obj = booking.check_out
            if isinstance(check_out_obj, str):
                check_out_obj = fields.Datetime.from_string(check_out_obj)
                
            new_check_out = datetime.combine(
                check_out_obj.date(),
                time(hour=target_out_h, minute=target_out_m)
            )
            time_updates['check_out'] = fields.Datetime.to_string(new_check_out)

        if time_updates:
            booking.write(time_updates)

        _logger.info(
            "Estado de reserva %s cambiado de '%s' a '%s'",
            reserva_id,
            old_status,
            final_status,
        )

        return self._prepare_response(
            {
                "success": True,
                "message": f'Estado cambiado de "{old_status}" a "{final_status}"',
                "data": {
                    "reserva_id": reserva_id,
                    "old_status": old_status,
                    "new_status": final_status,
                    "sequence_id": booking.sequence_id,
                },
            }
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>/send_email",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def send_reserva_email(self, reserva_id, **kw):
        """Enviar correo relacionado a la reserva"""
        booking = request.env["hotel.booking"].browse(reserva_id)
        if not booking.exists():
            return self._prepare_response(
                {
                    "success": False,
                    "error": f"La reserva con ID {reserva_id} no existe",
                },
                status=404,
            )

        self._check_access_rule(booking, "read")
        try:
            request.env["mail.template"].check_access_rights(
                "read", raise_exception=True
            )
        except AccessError:
            return self._prepare_response(
                {"success": False, "error": "No tiene permisos para enviar correos"},
                status=403,
            )

        data = self._parse_json_data()
        template_xml_id = data.get(
            "template_xml_id", "hotel_management_system.hotel_booking_confirm_id"
        )
        force_send = bool(data.get("force_send", True))
        email_values = data.get("email_values") or {}

        template = request.env.ref(template_xml_id, raise_if_not_found=False)
        if not template:
            raise ValueError(
                f'No se encontró la plantilla de correo "{template_xml_id}".'
            )

        mail_template = request.env["mail.template"].browse(template.id)
        try:
            mail_template.send_mail(
                booking.id,
                force_send=force_send,
                email_values=email_values if isinstance(email_values, dict) else {},
            )
        except Exception as exc:
            _logger.error(
                "Error enviando correo para la reserva %s: %s", reserva_id, str(exc)
            )
            raise ValueError(f"No se pudo enviar el correo: {str(exc)}")

        return self._prepare_response(
            {
                "success": True,
                "message": "Correo enviado correctamente",
                "data": {"reserva_id": booking.id, "template_xml_id": template_xml_id},
            }
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>/advance_payment",
        auth="public",
        type="http",
        methods=["POST"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def create_reserva_advance_payment(self, reserva_id, **kw):
        """Generar un anticipo para la orden de venta ligada a la reserva."""
        booking = request.env["hotel.booking"].browse(reserva_id)
        if not booking.exists():
            return self._prepare_response(
                {
                    "success": False,
                    "error": f"La reserva con ID {reserva_id} no existe",
                },
                status=404,
            )

        self._check_access_rule(booking, "read")
        self._check_access_rights("sale.order", "read")
        self._check_access_rights("account.move", "create")

        if not booking.order_id:
            raise ValueError(
                "La reserva no tiene una orden de venta asociada. Confirme la reserva primero."
            )
        self._check_access_rule(booking.order_id, "read")

        data = self._parse_json_data()
        method = data.get("advance_payment_method", "percentage")
        if method not in ["percentage", "fixed", "delivered"]:
            raise ValueError(
                'advance_payment_method debe ser "percentage", "fixed" o "delivered".'
            )

        wizard_vals = {"advance_payment_method": method}
        if method == "percentage":
            if data.get("amount") is None:
                raise ValueError(
                    'Debe especificar "amount" (porcentaje) para el anticipo.'
                )
            wizard_vals["amount"] = float(data["amount"])
        elif method == "fixed":
            if data.get("amount") is None:
                raise ValueError(
                    'Debe especificar "amount" (monto fijo) para el anticipo.'
                )
            wizard_vals["fixed_amount"] = float(data["amount"])
        else:
            wizard_vals["deduct_down_payments"] = bool(
                data.get("deduct_down_payments", True)
            )

        if data.get("product_id"):
            wizard_vals["product_id"] = int(data["product_id"])
        if data.get("consolidated_billing") is not None:
            wizard_vals["consolidated_billing"] = bool(data["consolidated_billing"])
        if data.get("deposit_account_id"):
            wizard_vals["deposit_account_id"] = int(data["deposit_account_id"])
        if data.get("deposit_taxes_id"):
            wizard_vals["deposit_taxes_id"] = [
                (6, 0, [int(t) for t in data["deposit_taxes_id"]])
            ]

        ctx = {
            "active_model": "sale.order",
            "active_id": booking.order_id.id,
            "active_ids": booking.order_id.ids,
            "default_sale_order_ids": booking.order_id.ids,
        }
        wizard_env = request.env["sale.advance.payment.inv"].with_context(ctx)
        wizard = wizard_env.create(wizard_vals)

        existing_invoice_ids = set(booking.order_id.invoice_ids.ids)
        wizard.create_invoices()
        booking.order_id.invalidate_recordset(["invoice_ids"])
        invoices = booking.order_id.invoice_ids.filtered(
            lambda inv: inv.id not in existing_invoice_ids
        )

        invoice_payload = [
            {
                "id": invoice.id,
                "name": invoice.name,
                "amount_total": invoice.amount_total,
                "currency_id": invoice.currency_id.id,
                "state": invoice.state,
            }
            for invoice in invoices
        ]

        return self._prepare_response(
            {
                "success": True,
                "message": "Anticipo creado exitosamente",
                "data": {
                    "reserva_id": booking.id,
                    "sale_order_id": booking.order_id.id,
                    "advance_payment_method": method,
                    "invoices_created": invoice_payload,
                },
            }
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>/advance_payment/options",
        auth="public",
        type="http",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def get_reserva_advance_payment_options(self, reserva_id, **kw):
        """Obtener valores predeterminados y opciones del wizard de anticipo."""
        booking = request.env["hotel.booking"].browse(reserva_id)
        if not booking.exists():
            return self._prepare_response(
                {
                    "success": False,
                    "error": f"La reserva con ID {reserva_id} no existe",
                },
                status=404,
            )
        if not booking.order_id:
            raise ValueError(
                "La reserva no tiene una orden de venta asociada. Confirme la reserva primero."
            )

        ctx = {
            "active_model": "sale.order",
            "active_id": booking.order_id.id,
            "active_ids": booking.order_id.ids,
            "default_sale_order_ids": booking.order_id.ids,
        }
        wizard_env = request.env["sale.advance.payment.inv"].with_context(ctx)
        wizard_record = wizard_env.new({})

        def _record_to_dict(record, fields_map):
            values = {}
            for key, getter in fields_map.items():
                values[key] = getter(record)
            return values

        defaults = _record_to_dict(
            wizard_record,
            {
                "advance_payment_method": lambda r: r.advance_payment_method,
                "amount": lambda r: r.amount,
                "fixed_amount": lambda r: r.fixed_amount,
                "has_down_payments": lambda r: bool(r.has_down_payments),
                "deduct_down_payments": lambda r: bool(r.deduct_down_payments),
                "consolidated_billing": lambda r: bool(r.consolidated_billing),
                "amount_invoiced": lambda r: r.amount_invoiced,
                "amount_to_invoice": lambda r: r.amount_to_invoice,
                "product_id": lambda r: r.product_id.id if r.product_id else None,
                "product_name": lambda r: (
                    r.product_id.display_name if r.product_id else None
                ),
                "currency": lambda r: {
                    "id": booking.order_id.currency_id.id,
                    "name": booking.order_id.currency_id.name,
                    "symbol": booking.order_id.currency_id.symbol,
                },
                "customer": lambda r: booking.order_id.partner_id.display_name,
                "date": lambda r: fields.Date.context_today(request.env.user),
            },
        )

        selection_field = wizard_record._fields["advance_payment_method"]
        selection_values = selection_field.selection
        if callable(selection_values):
            selection_values = selection_values(wizard_env.env)
        selection_options = [
            {"value": value, "label": label} for value, label in selection_values
        ]

        return self._prepare_response(
            {
                "success": True,
                "data": {
                    "defaults": defaults,
                    "advance_payment_methods": selection_options,
                },
            }
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>/update_guests",
        auth="public",
        type="http",
        methods=["POST", "PUT"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    def update_guests(self, reserva_id, **kw):
        """Agregar o actualizar huéspedes en una reserva existente"""
        try:
            booking = self._ensure_access(
                request.env["hotel.booking"].browse(reserva_id), "write"
            )
            if not booking.exists():
                return self._prepare_response(
                    {
                        "success": False,
                        "error": f"La reserva con ID {reserva_id} no existe",
                    },
                    status=404,
                )

            terminal_states = ["cancelled", "no_show", "checkout"]
            if booking.status_bar in terminal_states:
                return self._prepare_response(
                    {
                        "success": False,
                        "error": f'No se puede modificar una reserva en estado "{booking.status_bar}"',
                    },
                    status=400,
                )

            try:
                data = self._parse_json_data()
            except ValueError as e:
                return self._prepare_response(
                    {"success": False, "error": str(e)}, status=400
                )

            if not data:
                return self._prepare_response(
                    {
                        "success": False,
                        "error": "Debe proporcionar datos en formato JSON",
                    },
                    status=400,
                )

            guests_data = data.get("guests", [])
            if not guests_data:
                return self._prepare_response(
                    {
                        "success": False,
                        "error": "Debe proporcionar al menos un huésped",
                    },
                    status=400,
                )

            booking_line_id = data.get("booking_line_id")
            replace = data.get("replace", False)

            if booking_line_id:
                booking_line = request.env["hotel.booking.line"].browse(booking_line_id)
                if (
                    not booking_line.exists()
                    or booking_line.booking_id.id != reserva_id
                ):
                    return self._prepare_response(
                        {
                            "success": False,
                            "error": f"La línea de reserva con ID {booking_line_id} no existe o no pertenece a esta reserva",
                        },
                        status=404,
                    )
                booking_lines = booking_line
            else:
                booking_lines = booking.booking_line_ids

            if not booking_lines:
                return self._prepare_response(
                    {
                        "success": False,
                        "error": "La reserva no tiene líneas de habitación",
                    },
                    status=400,
                )

            for booking_line in booking_lines:
                if not replace and booking_line.guest_info_ids:
                    existing_guests = [
                        {
                            "name": existing_guest.name,
                            "age": existing_guest.age,
                            "gender": existing_guest.gender,
                            "partner_id": (
                                existing_guest.partner_id.id
                                if existing_guest.partner_id
                                else None
                            ),
                        }
                        for existing_guest in booking_line.guest_info_ids
                    ]
                    all_guests = existing_guests + guests_data
                else:
                    all_guests = guests_data

                try:
                    self._validate_guests_data(all_guests, booking_line.id)
                except ValueError as e:
                    return self._prepare_response(
                        {"success": False, "error": str(e)}, status=400
                    )

            guests_added = 0
            for booking_line in booking_lines:
                if replace:
                    booking_line.guest_info_ids.unlink()
                try:
                    self._create_guest_info(booking_line.id, guests_data)
                    guests_added += len(guests_data)
                except ValueError as e:
                    return self._prepare_response(
                        {"success": False, "error": str(e)}, status=400
                    )

            _logger.info(
                "Huéspedes actualizados en reserva %s: %d agregados",
                reserva_id,
                guests_added,
            )
            return self._prepare_response(
                {
                    "success": True,
                    "message": f"Se agregaron {guests_added} huésped(es) a la reserva",
                    "data": {
                        "reserva_id": reserva_id,
                        "guests_added": guests_added,
                        "booking": self._build_booking_data(booking),
                    },
                }
            )

        except ValueError as e:
            _logger.warning("Error de validación en update_guests: %s", str(e))
            return self._prepare_response(
                {"success": False, "error": str(e)}, status=400
            )
        except (AccessError, MissingError) as e:
            _logger.warning("Error de acceso en update_guests: %s", str(e))
            return self._prepare_response(
                {
                    "success": False,
                    "error": "No tiene permisos para modificar esta reserva",
                },
                status=403,
            )
        except Exception as e:
            _logger.exception("Error inesperado en update_guests: %s", str(e))
            return self._prepare_response(
                {"success": False, "error": "Error interno del servidor"}, status=500
            )
