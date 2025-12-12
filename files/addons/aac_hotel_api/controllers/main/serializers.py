# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import fields, _
from odoo.http import request
from .utils import ADULT_AGE_THRESHOLD


class HotelApiSerializers:
    """Mixin for serializing and deserializing Hotel API data"""

    def _get_room_change_chain(self, booking):
        """
        Rastrea toda la cadena de cambios de habitación para una reserva.
        """
        # Verificar acceso a la reserva
        booking_checked = self._ensure_access(booking, "read")
        chain = []
        visited = set()
        current = booking_checked

        # Rastrear hacia atrás para encontrar la reserva original
        while current and current.id not in visited:
            visited.add(current.id)
            chain.insert(
                0, current
            )  # Insertar al inicio para mantener orden cronológico

            # Buscar reserva anterior
            if (
                hasattr(current, "split_from_booking_id")
                and current.split_from_booking_id
            ):
                current = self._ensure_access(current.split_from_booking_id, "read")
            else:
                break

        # Rastrear hacia adelante desde la reserva original para encontrar todas las reservas siguientes
        if chain:
            original = chain[0]
            current = original

            # Buscar todas las reservas que tienen esta como split_from_booking_id
            while current:
                self._check_access_rights("hotel.booking", "read")
                next_bookings = request.env["hotel.booking"].search(
                    [("split_from_booking_id", "=", current.id)]
                )
                self._check_access_rule(next_bookings, "read")

                if next_bookings:
                    # Tomar la primera (debería haber solo una normalmente)
                    current = self._ensure_access(next_bookings[0], "read")
                    if current.id not in visited:
                        visited.add(current.id)
                        chain.append(current)
                    else:
                        break
                else:
                    break

        # Encontrar la posición de la reserva actual en la cadena
        current_position = None
        for i, b in enumerate(chain):
            if b.id == booking.id:
                current_position = i
                break

        return {
            "chain": chain,
            "original_booking": chain[0] if chain else None,
            "current_position": current_position,
            "total_changes": len(chain) - 1 if len(chain) > 1 else 0,
        }

    def _build_room_info_from_booking(self, booking):
        """Construir información de habitaciones de una reserva"""
        booking_checked = self._ensure_access(booking, "read")
        rooms = []
        if booking_checked and booking_checked.booking_line_ids:
            for line in booking_checked.booking_line_ids:
                if line.product_id:
                    rooms.append(
                        {
                            "id": line.product_id.id,
                            "name": line.product_id.name,
                            "code": line.product_id.default_code or "",
                            "template_id": (
                                line.product_id.product_tmpl_id.id
                                if hasattr(line.product_id, "product_tmpl_id")
                                and line.product_id.product_tmpl_id
                                else None
                            ),
                        }
                    )
        return rooms

    def _build_booking_data(self, booking):
        """Construir datos de respuesta de reserva de forma optimizada"""
        booking_checked = self._ensure_access(booking, "read")

        # Calcular información de horas para reservas por horas
        check_in_hour = None
        check_in_minute = None
        check_out_hour = None
        check_out_minute = None
        is_half_day_checkin = False
        is_half_day_checkout = False

        if booking.check_in:
            try:
                check_in_dt = booking.check_in
                if isinstance(check_in_dt, datetime):
                    check_in_hour = check_in_dt.hour
                    check_in_minute = check_in_dt.minute
                    is_half_day_checkin = check_in_hour >= 12
            except Exception:
                pass

        if booking.check_out:
            try:
                check_out_dt = booking.check_out
                if isinstance(check_out_dt, datetime):
                    check_out_hour = check_out_dt.hour
                    check_out_minute = check_out_dt.minute
                    is_half_day_checkout = check_out_hour < 12
            except Exception:
                pass

        booking_data = {
            "id": booking.id,
            "sequence_id": booking.sequence_id,
            "partner_id": booking.partner_id.id if booking.partner_id else None,
            "partner_name": booking.partner_id.name,
            "check_in": booking.check_in,
            "check_out": booking.check_out,
            "status_bar": booking.status_bar,
            "check_in_hour": check_in_hour,
            "check_in_minute": check_in_minute,
            "check_out_hour": check_out_hour,
            "check_out_minute": check_out_minute,
            "is_half_day_checkin": is_half_day_checkin,
            "is_half_day_checkout": is_half_day_checkout,
            "hotel_id": booking.hotel_id.id if booking.hotel_id else None,
            "hotel_name": booking.hotel_id.name if booking.hotel_id else None,
            "motivo_viaje": booking.motivo_viaje or "",
            "responsible_name": booking.user_id.name if booking.user_id else None,
            "user_id": booking.user_id.id if booking.user_id else None,
            "description": booking.description or "",
            "booking_date": booking.booking_date,
            "create_date": booking.create_date,
            "write_date": booking.write_date,
            "booking_reference": booking.booking_reference,
            "origin": booking.origin or "",
            "pricelist_id": booking.pricelist_id.id if booking.pricelist_id else None,
            "pricelist_name": (
                booking.pricelist_id.name if booking.pricelist_id else None
            ),
            "currency_id": booking.currency_id.id if booking.currency_id else None,
            "currency_symbol": (
                booking.currency_id.symbol if booking.currency_id else None
            ),
            "amount_untaxed": booking.amount_untaxed,
            "total_amount": booking.total_amount,
            "booking_discount": booking.booking_discount,
            "tax_amount": booking.tax_amount,
            "booking_days": booking.booking_days,
            "cancellation_reason": booking.cancellation_reason or "",
            "via_agent": booking.via_agent,
            "agent_id": booking.agent_id.id if booking.agent_id else None,
            "agent_name": booking.agent_id.name if booking.agent_id else None,
            "commission_type": booking.commission_type or "",
            "agent_commission_amount": booking.agent_commission_amount,
            "agent_commission_percentage": booking.agent_commission_percentage,
            "company_id": booking.company_id.id if booking.company_id else None,
            "company_name": booking.company_id.name if booking.company_id else None,
        }

        # Información de órdenes de venta
        primary_order = booking.order_id
        if primary_order:
            booking_data.update(
                {
                    "order_id": primary_order.id,
                    "order_name": primary_order.name,
                    "order_state": primary_order.state,
                    "order_amount_total": primary_order.amount_total,
                    "order_currency_id": (
                        primary_order.currency_id.id
                        if primary_order.currency_id
                        else None
                    ),
                    "order_currency_symbol": (
                        primary_order.currency_id.symbol
                        if primary_order.currency_id
                        else None
                    ),
                }
            )
        else:
            booking_data.update(
                {
                    "order_id": None,
                    "order_name": None,
                    "order_state": None,
                    "order_amount_total": 0.0,
                    "order_currency_id": (
                        booking.currency_id.id if booking.currency_id else None
                    ),
                    "order_currency_symbol": (
                        booking.currency_id.symbol if booking.currency_id else None
                    ),
                }
            )

        # Verificar permisos antes de buscar órdenes de venta
        self._check_access_rights("sale.order", "read")
        related_orders = request.env["sale.order"].search(
            [("booking_id", "=", booking.id)]
        )
        self._check_access_rule(related_orders, "read")

        booking_data["sale_orders"] = [
            {
                "id": order.id,
                "name": order.name,
                "state": order.state,
                "amount_total": order.amount_total,
                "currency_id": order.currency_id.id if order.currency_id else None,
                "currency_symbol": (
                    order.currency_id.symbol if order.currency_id else None
                ),
            }
            for order in related_orders
        ]

        # Campos de la extensión
        extension_fields = [
            "early_checkin_charge",
            "late_checkout_charge",
            "additional_charges_total",
            "discount_reason",
            "manual_service_description",
            "manual_service_amount",
        ]
        for field in extension_fields:
            if hasattr(booking, field):
                booking_data[field] = getattr(booking, field) or (
                    0 if "amount" in field or "charge" in field else ""
                )

        # Campos relacionales de la extensión
        if (
            hasattr(booking, "early_checkin_product_id")
            and booking.early_checkin_product_id
        ):
            booking_data["early_checkin_product_id"] = (
                booking.early_checkin_product_id.id
            )
            booking_data["early_checkin_product_name"] = (
                booking.early_checkin_product_id.name
            )

        if (
            hasattr(booking, "late_checkout_product_id")
            and booking.late_checkout_product_id
        ):
            booking_data["late_checkout_product_id"] = (
                booking.late_checkout_product_id.id
            )
            booking_data["late_checkout_product_name"] = (
                booking.late_checkout_product_id.name
            )

        # Información de cambio de habitación
        is_room_change_origin = False
        is_room_change_destination = False
        connected_booking_id = None
        split_from_booking_id = None

        current_rooms = self._build_room_info_from_booking(booking_checked)
        change_chain = self._get_room_change_chain(booking_checked)
        chain = change_chain["chain"]
        current_position = change_chain["current_position"]
        total_changes = change_chain["total_changes"]

        if len(chain) > 1:
            booking_data["has_room_change"] = True

            if current_position == 0:
                is_room_change_origin = True
            elif current_position == len(chain) - 1:
                is_room_change_destination = True
            elif current_position is not None and current_position > 0:
                is_room_change_destination = True

            booking_data["is_room_change_origin"] = is_room_change_origin
            booking_data["is_room_change_destination"] = is_room_change_destination or (
                current_position is not None and current_position > 0
            )

            if (
                hasattr(booking_checked, "connected_booking_id")
                and booking_checked.connected_booking_id
            ):
                connected_booking_id = booking_checked.connected_booking_id.id
                booking_data["connected_booking_id"] = connected_booking_id
                booking_data["connected_booking_sequence"] = (
                    booking_checked.connected_booking_id.sequence_id
                )
                connected_booking = self._ensure_access(
                    booking_checked.connected_booking_id, "read"
                )
                booking_data["connected_booking"] = {
                    "id": connected_booking.id,
                    "sequence_id": connected_booking.sequence_id,
                    "check_in": connected_booking.check_in,
                    "check_out": connected_booking.check_out,
                    "status_bar": connected_booking.status_bar,
                    "partner_name": (
                        connected_booking.partner_id.name
                        if connected_booking.partner_id
                        else None
                    ),
                    "rooms": self._build_room_info_from_booking(connected_booking),
                }

            if (
                hasattr(booking_checked, "split_from_booking_id")
                and booking_checked.split_from_booking_id
            ):
                split_from_booking_id = booking_checked.split_from_booking_id.id
                booking_data["split_from_booking_id"] = split_from_booking_id
                booking_data["split_from_booking_sequence"] = (
                    booking_checked.split_from_booking_id.sequence_id
                )
                original_booking_obj = self._ensure_access(
                    booking_checked.split_from_booking_id, "read"
                )
                booking_data["original_booking"] = {
                    "id": original_booking_obj.id,
                    "sequence_id": original_booking_obj.sequence_id,
                    "check_in": original_booking_obj.check_in,
                    "check_out": original_booking_obj.check_out,
                    "status_bar": original_booking_obj.status_bar,
                    "partner_name": (
                        original_booking_obj.partner_id.name
                        if original_booking_obj.partner_id
                        else None
                    ),
                    "rooms": self._build_room_info_from_booking(original_booking_obj),
                }

            room_change_chain = []
            for i, chain_booking in enumerate(chain):
                chain_rooms = self._build_room_info_from_booking(chain_booking)
                room_change_chain.append(
                    {
                        "booking_id": chain_booking.id,
                        "sequence_id": chain_booking.sequence_id,
                        "check_in": chain_booking.check_in,
                        "check_out": chain_booking.check_out,
                        "status_bar": chain_booking.status_bar,
                        "position": i,
                        "is_original": i == 0,
                        "is_last": i == len(chain) - 1,
                        "is_current": chain_booking.id == booking.id,
                        "rooms": chain_rooms,
                    }
                )

            original_room = None
            new_room = None

            if current_position is not None:
                if current_position > 0:
                    previous_booking = chain[current_position - 1]
                    prev_rooms = self._build_room_info_from_booking(previous_booking)
                    original_room = prev_rooms[0] if prev_rooms else None

                new_room = current_rooms[0] if current_rooms else None

                if current_position < len(chain) - 1:
                    next_booking = chain[current_position + 1]
                    next_rooms = self._build_room_info_from_booking(next_booking)
                    if not new_room and next_rooms:
                        new_room = next_rooms[0]

            booking_data["room_change_info"] = {
                "is_room_change": True,
                "is_origin": is_room_change_origin,
                "is_destination": is_room_change_destination
                or (current_position is not None and current_position > 0),
                "connected_booking_id": connected_booking_id,
                "split_from_booking_id": split_from_booking_id,
                "original_room": original_room,
                "new_room": new_room,
                "total_changes": total_changes,
                "current_position": current_position,
                "chain_length": len(chain),
            }
            booking_data["room_change_chain"] = room_change_chain
        else:
            booking_data["has_room_change"] = False
            booking_data["is_room_change_origin"] = False
            booking_data["is_room_change_destination"] = False
            booking_data["room_change_info"] = {
                "is_room_change": False,
                "is_origin": False,
                "is_destination": False,
                "connected_booking_id": None,
                "split_from_booking_id": None,
                "original_room": None,
                "new_room": None,
                "total_changes": 0,
                "current_position": None,
                "chain_length": 1,
            }
            booking_data["room_change_chain"] = []

        booking_data["rooms"] = self._build_room_lines(booking.booking_line_ids)
        booking_data["documents"] = self._build_documents_data(booking.docs_ids)

        booking_data["booking_line_sequence_ids"] = [
            line.booking_sequence_id
            for line in booking.booking_line_ids
            if line.booking_sequence_id
        ]

        has_room_change = booking_data.get("has_room_change", False)
        is_multiple_booking = len(booking.booking_line_ids) > 1
        booking_data["show_sync_services_button"] = (
            has_room_change or is_multiple_booking
        )

        return booking_data

    def _build_room_lines(self, booking_lines):
        room_lines = []
        for line in booking_lines:
            guest_list = [
                {
                    "id": guest.id,
                    "name": guest.name,
                    "age": guest.age,
                    "gender": guest.gender,
                    "is_adult": getattr(
                        guest, "is_adult", guest.age >= ADULT_AGE_THRESHOLD
                    ),
                }
                for guest in line.guest_info_ids
            ]

            line_data = {
                "id": line.id,
                "booking_sequence_id": line.booking_sequence_id,
                "product_id": line.product_id.id if line.product_id else None,
                "product_tmpl_id": (
                    line.product_tmpl_id.id
                    if hasattr(line, "product_tmpl_id") and line.product_tmpl_id
                    else None
                ),
                "room_name": line.product_id.name if line.product_id else None,
                "room_id": line.product_id.id if line.product_id else None,
                "room_code": (
                    getattr(line.product_id, "default_code", None)
                    if line.product_id
                    else None
                ),
                "room_barcode": (
                    getattr(line.product_id, "barcode", None)
                    if line.product_id
                    else None
                ),
                "guest_info": guest_list,
                "max_adult": getattr(line, "max_adult", None),
                "max_child": getattr(line, "max_child", None),
                "booking_days": line.booking_days,
                "price": line.price,
                "discount": getattr(line, "discount", 0.0),
                "subtotal_price": getattr(line, "subtotal_price", 0.0),
                "taxed_price": getattr(line, "taxed_price", 0.0),
                "description": line.description or "",
                "status_bar": line.status_bar,
                "tax_ids": (
                    [tax.id for tax in line.tax_ids] if hasattr(line, "tax_ids") else []
                ),
                "currency_id": (
                    line.currency_id.id
                    if hasattr(line, "currency_id") and line.currency_id
                    else None
                ),
                "currency_symbol": (
                    line.currency_id.symbol
                    if hasattr(line, "currency_id") and line.currency_id
                    else None
                ),
            }

            for field in ["discount_amount", "discount_reason", "discount_percentage"]:
                if hasattr(line, field):
                    line_data[field] = getattr(line, field) or (
                        0.0 if "amount" in field or "percentage" in field else ""
                    )

            if hasattr(line, "is_room_change_segment"):
                line_data["is_room_change_segment"] = line.is_room_change_segment

            if hasattr(line, "previous_line_id") and line.previous_line_id:
                line_data["previous_line_id"] = line.previous_line_id.id
                line_data["previous_line_sequence"] = getattr(
                    line.previous_line_id, "booking_sequence_id", None
                )

            if hasattr(line, "next_line_id") and line.next_line_id:
                line_data["next_line_id"] = line.next_line_id.id
                line_data["next_line_sequence"] = getattr(
                    line.next_line_id, "booking_sequence_id", None
                )

            room_lines.append(line_data)
        return room_lines

    def _build_documents_data(self, docs_ids):
        return [
            {
                "id": doc.id,
                "name": doc.name,
                "file_name": doc.file_name,
                "file_size": len(doc.file) if doc.file else 0,
                "has_file": bool(doc.file),
            }
            for doc in docs_ids
        ]

    def _create_booking_lines(self, booking_id, rooms_data):
        booking = request.env["hotel.booking"].browse(booking_id)

        for room_data in rooms_data:
            product_id = room_data.get("product_id") or room_data.get("room_id")
            if not product_id:
                continue

            booking_line_vals = {
                "booking_id": booking_id,
                "product_id": product_id,
            }

            if room_data.get("booking_days"):
                booking_line_vals["booking_days"] = room_data["booking_days"]

            if room_data.get("price"):
                booking_line_vals["price"] = float(room_data["price"])
            else:
                product = request.env["product.product"].browse(product_id)
                if booking.pricelist_id:
                    booking_line_vals["price"] = (
                        booking.pricelist_id._get_product_price(product, 1)
                    )
                else:
                    booking_line_vals["price"] = product.list_price

            if room_data.get("discount") is not None:
                booking_line_vals["discount"] = float(room_data["discount"])

            if room_data.get("tax_ids"):
                tax_ids = (
                    room_data["tax_ids"]
                    if isinstance(room_data["tax_ids"], list)
                    else [room_data["tax_ids"]]
                )
                booking_line_vals["tax_ids"] = [(6, 0, tax_ids)]
            else:
                # Si no se especifican tax_ids, copiar los impuestos del producto
                product = request.env["product.product"].browse(product_id)
                if product.taxes_id:
                    booking_line_vals["tax_ids"] = [(6, 0, product.taxes_id.ids)]

            if room_data.get("description"):
                booking_line_vals["description"] = room_data["description"]

            booking_line = request.env["hotel.booking.line"].create(booking_line_vals)

            if room_data.get("guests"):
                self._create_guest_info(booking_line.id, room_data["guests"])
            elif booking.partner_id:
                default_guest = {
                    "partner_id": booking.partner_id.id,
                    "name": booking.partner_id.name,
                    "age": 30,
                    "gender": "male",
                }
                self._create_guest_info(booking_line.id, [default_guest])

    def _create_guest_info(self, booking_line_id, guests_data):
        for guest_data in guests_data:
            if guest_data.get("partner_id"):
                partner = request.env["res.partner"].browse(guest_data["partner_id"])
                if not partner.exists():
                    raise ValueError(
                        f'El partner con ID {guest_data["partner_id"]} no existe'
                    )
                guest_name = partner.name
            else:
                guest_name = guest_data.get("name", "")

            if not guest_name:
                raise ValueError(
                    "Debe especificar el nombre del huésped o un partner_id válido"
                )

            guest_age = guest_data.get("age")
            if not guest_age:
                raise ValueError("Debe especificar la edad del huésped")

            guest_vals = {
                "booking_line_id": booking_line_id,
                "name": guest_name,
                "age": int(guest_age),
                "gender": guest_data.get("gender", "male"),
            }

            if guest_data.get("partner_id"):
                guest_vals["partner_id"] = guest_data["partner_id"]

            request.env["guest.info"].create(guest_vals)

    def _create_documents(self, booking_id, documents_data):
        for doc_data in documents_data:
            if not doc_data.get("name"):
                continue

            doc_vals = {
                "booking_id": booking_id,
                "name": doc_data["name"],
                "file_name": doc_data.get("file_name", "Document"),
            }

            if doc_data.get("file"):
                doc_vals["file"] = doc_data["file"]

            request.env["hotel.document"].create(doc_vals)

    def _build_domain_from_filters(self, **filters):
        domain = []

        hotel_id_param = filters.get("hotel_id")
        if hotel_id_param is not None and hotel_id_param != "":
            try:
                hotel_id = self._validate_hotel_id(hotel_id_param)
                domain.append(("hotel_id", "=", hotel_id))
            except ValueError:
                raise

        if filters.get("partner_id"):
            partner_id = self._validate_partner_id(filters["partner_id"])
            domain.append(("partner_id", "=", partner_id))

        if filters.get("user_id"):
            try:
                user_id = int(filters["user_id"])
                domain.append(("user_id", "=", user_id))
            except (ValueError, TypeError):
                raise ValueError("El user_id debe ser un número entero válido")

        if filters.get("status_bar"):
            status = filters["status_bar"]
            self._validate_booking_status(status)
            domain.append(("status_bar", "=", status))

        return domain
