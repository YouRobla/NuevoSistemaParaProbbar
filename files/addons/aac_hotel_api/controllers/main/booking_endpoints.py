# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import http, _
from odoo.http import request
from ..api_auth import validate_api_key
from .utils import handle_api_errors, TERMINAL_STATUSES

_logger = logging.getLogger(__name__)


class BookingEndpoints:

    @http.route(
        "/api/hotel/reservas/<int:hotel_id>",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def get_reservas_by_hotel_id(self, hotel_id, **kw):
        """Obtener reservas por ID de hotel"""
        self._check_access_rights("hotel.hotels", "read")
        hotel = request.env["hotel.hotels"].browse(hotel_id)
        if not hotel.exists():
            return self._prepare_response(
                {"success": False, "error": f"El hotel con ID {hotel_id} no existe"},
                status=404,
            )
        self._check_access_rule(hotel, "read")

        filters = dict(kw, hotel_id=hotel_id)
        domain = self._build_domain_from_filters(**filters)

        status_bar_param = kw.get("status_bar")
        if not status_bar_param or status_bar_param not in ["cancel", "cancelled"]:
            domain.append(("status_bar", "not in", ["cancel", "cancelled"]))

        self._check_access_rights("hotel.booking", "read")
        booking_records = request.env["hotel.booking"].search(domain)
        self._check_access_rule(booking_records, "read")

        reservas_list = [
            self._build_booking_data(booking) for booking in booking_records
        ]

        _logger.info(
            "Consulta exitosa: %s reservas recuperadas para hotel %s (%s)",
            len(reservas_list),
            hotel_id,
            hotel.name,
        )

        return self._prepare_response(
            {
                "success": True,
                "count": len(reservas_list),
                "hotel_id": hotel_id,
                "hotel_name": hotel.name,
                "data": reservas_list,
            }
        )

    @http.route(
        "/api/hotel/reservas/habitacion/<int:room_id>",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def get_reservas_by_room_id(self, room_id, **kw):
        """Obtener reservas por ID de habitación"""
        self._check_access_rights("product.product", "read")
        product = request.env["product.product"].browse(room_id)
        if not product.exists():
            return self._prepare_response(
                {"success": False, "error": f"El producto con ID {room_id} no existe"},
                status=404,
            )
        self._check_access_rule(product, "read")

        is_room_type = product.is_room_type
        if is_room_type:
            room_type_message = "Es tipo de habitación"
        else:
            room_type_message = "No es tipo de habitación"
            _logger.warning(
                "Consulta de reservas por producto ID %s que no es tipo habitación: %s",
                room_id,
                product.name,
            )

        booking_lines_domain = [("product_id", "=", room_id)]

        booking_ids_with_hotel = None
        if kw.get("hotel_id") or kw.get("hotel"):
            hotel_id_param = kw.get("hotel_id") or kw.get("hotel")
            try:
                hotel_id = self._validate_hotel_id(hotel_id_param)
                self._check_access_rights("hotel.booking", "read")
                booking_ids_with_hotel = (
                    request.env["hotel.booking"]
                    .search([("hotel_id", "=", hotel_id)])
                    .ids
                )

                if booking_ids_with_hotel:
                    booking_lines_domain = booking_lines_domain + [
                        ("booking_id", "in", booking_ids_with_hotel)
                    ]
                else:
                    return self._prepare_response(
                        {
                            "success": True,
                            "count": 0,
                            "room_id": room_id,
                            "room_name": product.name,
                            "is_room_type": is_room_type,
                            "room_type_message": room_type_message,
                            "data": [],
                        }
                    )
            except ValueError:
                pass

        self._check_access_rights("hotel.booking.line", "read")
        booking_lines = request.env["hotel.booking.line"].search(booking_lines_domain)
        booking_ids_with_room = booking_lines.mapped("booking_id").ids

        if not booking_ids_with_room:
            return self._prepare_response(
                {
                    "success": True,
                    "count": 0,
                    "room_id": room_id,
                    "room_name": product.name,
                    "is_room_type": is_room_type,
                    "room_type_message": room_type_message,
                    "data": [],
                }
            )

        filters = {k: v for k, v in kw.items() if k not in ("hotel_id", "hotel")}
        domain = self._build_domain_from_filters(**filters)

        status_bar_param = kw.get("status_bar")
        if not status_bar_param or status_bar_param not in ["cancel", "cancelled"]:
            domain.append(("status_bar", "not in", ["cancel", "cancelled"]))

        domain = domain + [("id", "in", booking_ids_with_room)]

        self._check_access_rights("hotel.booking", "read")
        booking_records = request.env["hotel.booking"].search(domain)
        self._check_access_rule(booking_records, "read")

        reservas_list = [
            self._build_booking_data(booking) for booking in booking_records
        ]

        return self._prepare_response(
            {
                "success": True,
                "count": len(reservas_list),
                "room_id": room_id,
                "room_name": product.name,
                "room_code": product.default_code or "",
                "is_room_type": is_room_type,
                "room_type_message": room_type_message,
                "data": reservas_list,
            }
        )

    @http.route(
        "/api/hotel/reservas",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def get_reservas(self, **kw):
        """Obtener todas las reservas con filtros opcionales"""
        cleaned_kw = {k: v for k, v in kw.items() if v not in (None, "", "None")}
        if "hotel" in cleaned_kw and "hotel_id" not in cleaned_kw:
            cleaned_kw["hotel_id"] = cleaned_kw.pop("hotel")

        domain = self._build_domain_from_filters(**cleaned_kw)

        hotel_id_param = cleaned_kw.get("hotel_id")
        if hotel_id_param:
            has_hotel_filter = any(
                isinstance(term, tuple) and len(term) == 3 and term[0] == "hotel_id"
                for term in domain
            )
            if not has_hotel_filter:
                try:
                    hotel_id = self._validate_hotel_id(hotel_id_param)
                    domain.append(("hotel_id", "=", hotel_id))
                except Exception:
                    raise

        room_id_param = cleaned_kw.get("room_id") or cleaned_kw.get("product_id")
        room_type_info = None
        if room_id_param:
            try:
                room_id = int(room_id_param)
                product = request.env["product.product"].browse(room_id)
                if not product.exists():
                    return self._prepare_response(
                        {
                            "success": False,
                            "error": f"El producto con ID {room_id} no existe",
                        },
                        status=404,
                    )

                is_room_type = product.is_room_type
                room_type_info = {
                    "room_id": room_id,
                    "room_name": product.name,
                    "is_room_type": is_room_type,
                    "room_type_message": (
                        "Es tipo de habitación"
                        if is_room_type
                        else "No es tipo de habitación"
                    ),
                }

                booking_ids_with_hotel = None
                if cleaned_kw.get("hotel_id"):
                    hotel_id = self._validate_hotel_id(cleaned_kw["hotel_id"])
                    booking_ids_with_hotel = (
                        request.env["hotel.booking"]
                        .search([("hotel_id", "=", hotel_id)])
                        .ids
                    )
                    if not booking_ids_with_hotel:
                        response_data = {"success": True, "count": 0, "data": []}
                        response_data.update(room_type_info)
                        return self._prepare_response(response_data)

                booking_lines_domain = [("product_id", "=", room_id)]
                if booking_ids_with_hotel:
                    booking_lines_domain = booking_lines_domain + [
                        ("booking_id", "in", booking_ids_with_hotel)
                    ]

                booking_lines = request.env["hotel.booking.line"].search(
                    booking_lines_domain
                )
                booking_ids_with_room = booking_lines.mapped("booking_id").ids

                if booking_ids_with_room:
                    if domain:
                        domain = domain + [("id", "in", booking_ids_with_room)]
                    else:
                        domain = [("id", "in", booking_ids_with_room)]
                else:
                    response_data = {"success": True, "count": 0, "data": []}
                    response_data.update(room_type_info)
                    return self._prepare_response(response_data)
            except (ValueError, TypeError):
                raise ValueError(
                    "El room_id/product_id debe ser un número entero válido"
                )

        if not domain and cleaned_kw:
            other_filters = {
                k: v
                for k, v in cleaned_kw.items()
                if k not in ("room_id", "product_id", "hotel")
            }
            if other_filters:
                domain = [("id", "=", -1)]

        status_bar_param = cleaned_kw.get("status_bar")
        if not status_bar_param or status_bar_param not in ["cancel", "cancelled"]:
            domain.append(("status_bar", "not in", ["cancel", "cancelled"]))

        booking_records = request.env["hotel.booking"].sudo().search(domain)
        reservas_list = [
            self._build_booking_data(booking) for booking in booking_records
        ]

        _logger.info("Consulta exitosa: %s reservas recuperadas", len(reservas_list))

        response_data = {
            "success": True,
            "count": len(reservas_list),
            "data": reservas_list,
        }
        if cleaned_kw.get("hotel_id"):
            try:
                hotel_id = int(cleaned_kw["hotel_id"])
                hotel = request.env["hotel.hotels"].browse(hotel_id)
                if hotel.exists():
                    response_data["hotel_id"] = hotel_id
                    response_data["hotel_name"] = hotel.name
            except (ValueError, TypeError):
                pass

        if room_type_info:
            response_data.update(room_type_info)

        return self._prepare_response(response_data)

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def get_reserva_by_id(self, reserva_id, **kw):
        """Obtener una reserva específica por ID"""
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
        return self._prepare_response(
            {"success": True, "data": self._build_booking_data(booking)}
        )

    @http.route(
        "/api/hotel/reserva",
        auth="public",
        type="http",
        methods=["POST", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def create_reserva(self, **kw):
        """Crear una nueva reserva"""
        data = self._parse_json_data()

        required_fields = ["partner_id", "check_in", "check_out", "rooms", "user_id"]
        self._validate_required_fields(data, required_fields)

        check_in, check_out = self._validate_dates(data["check_in"], data["check_out"])
        self._validate_partner_id(data["partner_id"])
        self._validate_rooms_data(data["rooms"])

        if data.get("status_bar") in ["checked_in", "check_in"]:
            data["status_bar"] = "checkin"

        self._validate_booking_status(data.get("status_bar"))
        if data.get("hotel_id"):
            self._validate_hotel_id(data["hotel_id"])
        self._validate_booking_reference(data.get("booking_reference"))
        self._validate_agent_data(data)
        self._validate_documents_data(data.get("documents"))

        self._check_access_rights("hotel.booking", "create")
        self._check_access_rights("hotel.booking.line", "create")

        booking_vals = {
            "partner_id": data["partner_id"],
            "user_id": data["user_id"],
            "check_in": check_in,
            "check_out": check_out,
            "status_bar": data.get("status_bar", "initial"),
            "booking_date": datetime.now(),
        }

        optional_fields = {
            "hotel_id": int,
            "product_tmpl_id": int,
            "pricelist_id": int,
            "origin": str,
            "booking_discount": float,
            "booking_reference": str,
            "description": str,
            "company_id": int,
            "cancellation_reason": str,
        }
        for field, field_type in optional_fields.items():
            if data.get(field) is not None:
                booking_vals[field] = field_type(data[field])

        if data.get("booking_date"):
            try:
                booking_vals["booking_date"] = self._parse_datetime(
                    data["booking_date"], "booking_date"
                )
            except ValueError:
                booking_vals["booking_date"] = datetime.now()

        extension_fields = {
            "motivo_viaje": str,
            "early_checkin_charge": float,
            "late_checkout_charge": float,
            "early_checkin_product_id": int,
            "late_checkout_product_id": int,
            "discount_reason": str,
            "connected_booking_id": int,
            "split_from_booking_id": int,
            "manual_service_description": str,
            "manual_service_amount": float,
        }
        for field, field_type in extension_fields.items():
            if data.get(field) is not None:
                booking_vals[field] = field_type(data[field])

        if data.get("via_agent"):
            booking_vals.update(
                {
                    "via_agent": True,
                    "agent_id": data.get("agent_id"),
                    "commission_type": data.get("commission_type", "fixed"),
                    "agent_commission_amount": float(
                        data.get("agent_commission_amount", 0.0)
                    ),
                    "agent_commission_percentage": float(
                        data.get("agent_commission_percentage", 0.0)
                    ),
                }
            )

        nueva_reserva = request.env["hotel.booking"].create(booking_vals)
        self._create_booking_lines(nueva_reserva.id, data["rooms"])

        _logger.info(
            "Reserva %s (%s) creada exitosamente por usuario %s",
            nueva_reserva.id,
            nueva_reserva.sequence_id,
            request.env.user.name,
        )

        return self._prepare_response(
            {
                "success": True,
                "message": "Reserva creada exitosamente",
                "data": {
                    "reserva_id": nueva_reserva.id,
                    "sequence_id": nueva_reserva.sequence_id,
                    "partner_name": nueva_reserva.partner_id.name,
                    "check_in": nueva_reserva.check_in,
                    "check_out": nueva_reserva.check_out,
                    "status_bar": nueva_reserva.status_bar,
                    "total_amount": nueva_reserva.total_amount,
                },
            },
            status=201,
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>",
        auth="public",
        type="http",
        methods=["PUT", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def update_reserva(self, reserva_id, **kw):
        """Actualizar una reserva existente"""
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
        self._validate_booking_for_update(booking, data)

        update_vals = {}
        if data.get("check_in") or data.get("check_out"):
            check_in_str = data.get("check_in", booking.check_in)
            check_out_str = data.get("check_out", booking.check_out)
            check_in, check_out = self._validate_dates(check_in_str, check_out_str)
            update_vals["check_in"] = check_in
            update_vals["check_out"] = check_out

        if data.get("partner_id"):
            update_vals["partner_id"] = self._validate_partner_id(data["partner_id"])
        if data.get("hotel_id"):
            update_vals["hotel_id"] = self._validate_hotel_id(data["hotel_id"])

        new_status = data.get("status_bar")
        if new_status:
            if new_status in ["checked_in", "check_in"]:
                new_status = "checkin"
            self._validate_status_transition(booking.status_bar, new_status)
            update_vals["status_bar"] = new_status

        updatable_fields = [
            "user_id",
            "motivo_viaje",
            "description",
            "booking_discount",
            "cancellation_reason",
            "origin",
            "pricelist_id",
            "company_id",
            "early_checkin_charge",
            "late_checkout_charge",
            "discount_reason",
            "manual_service_description",
            "manual_service_amount",
        ]
        for field in updatable_fields:
            if data.get(field) is not None:
                update_vals[field] = data[field]

        if "via_agent" in data:
            if data["via_agent"]:
                self._validate_agent_data(data)
                update_vals.update(
                    {
                        "via_agent": True,
                        "agent_id": data.get("agent_id"),
                        "commission_type": data.get("commission_type"),
                        "agent_commission_amount": data.get(
                            "agent_commission_amount", 0.0
                        ),
                        "agent_commission_percentage": data.get(
                            "agent_commission_percentage", 0.0
                        ),
                    }
                )
            else:
                update_vals["via_agent"] = False

        if update_vals:
            booking.write(update_vals)
            _logger.info("Reserva %s actualizada exitosamente", reserva_id)

        return self._prepare_response(
            {
                "success": True,
                "message": "Reserva actualizada exitosamente",
                "data": self._build_booking_data(booking),
            }
        )

    @http.route(
        "/api/hotel/reserva/<int:reserva_id>",
        auth="public",
        type="http",
        methods=["DELETE", "OPTIONS"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def delete_reserva(self, reserva_id, **kw):
        """Eliminar (cancelar) una reserva"""
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
        force_delete = kw.get("force", "").lower() in ["true", "1", "yes"]

        if force_delete:
            self._check_access_rights("hotel.booking", "unlink")
            self._check_access_rule(booking, "unlink")
            sequence_id = booking.sequence_id
            booking.unlink()
            _logger.info(
                "Reserva %s (%s) eliminada físicamente", reserva_id, sequence_id
            )
            return self._prepare_response(
                {
                    "success": True,
                    "message": "Reserva eliminada permanentemente",
                    "reserva_id": reserva_id,
                    "sequence_id": sequence_id,
                }
            )
        else:
            self._check_access_rights("hotel.booking", "write")
            self._check_access_rule(booking, "write")
            if booking.status_bar == "cancelled":
                return self._prepare_response(
                    {"success": False, "error": "La reserva ya está cancelada"},
                    status=400,
                )
            booking.write({"status_bar": "cancelled"})
            _logger.info("Reserva %s (%s) cancelada", reserva_id, booking.sequence_id)
            return self._prepare_response(
                {
                    "success": True,
                    "message": "Reserva cancelada exitosamente",
                    "data": self._build_booking_data(booking),
                }
            )
