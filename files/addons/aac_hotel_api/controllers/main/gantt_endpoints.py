# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from odoo import http, fields, _
from odoo.http import request
from ..api_auth import validate_api_key
from .utils import handle_api_errors

_logger = logging.getLogger(__name__)


class GanttEndpoints:

    @http.route(
        "/api/hotel/gantt/data",
        auth="public",
        type="http",
        methods=["GET"],
        csrf=False,
        website=False,
    )
    @validate_api_key
    @handle_api_errors
    def get_gantt_data(self, **kw):
        """Obtener datos del Gantt con información completa de horas para reservas (optimizado para React)"""
        try:
            target_date_str = kw.get("target_date")
            target_date = (
                datetime.strptime(target_date_str, "%Y-%m-%d").date()
                if target_date_str
                else datetime.now().date()
            )

            hotel_id = kw.get("hotel_id")
            if hotel_id:
                try:
                    hotel_id = int(hotel_id)
                except (ValueError, TypeError):
                    hotel_id = None

            domain = [("is_room_type", "=", True)]
            if hotel_id:
                domain.append(("hotel_id", "=", hotel_id))

            rooms = (
                request.env["product.template"]
                .sudo()
                .search_read(
                    domain,
                    fields=[
                        "id",
                        "name",
                        "list_price",
                        "max_adult",
                        "max_child",
                        "hotel_id",
                    ],
                    order="name",
                    limit=1000,
                )
            )

            for room in rooms:
                room["room_type_id"] = False
                max_adult = room.get("max_adult", 1)
                max_child = room.get("max_child", 0)
                room["capacity"] = max_adult + max_child
                room["price"] = room.get("list_price", 0.0)

                original_hotel_id = room.get("hotel_id")
                if original_hotel_id:
                    if (
                        isinstance(original_hotel_id, (list, tuple))
                        and len(original_hotel_id) >= 2
                    ):
                        room["hotel_id"] = (
                            list(original_hotel_id)
                            if isinstance(original_hotel_id, tuple)
                            else original_hotel_id
                        )
                    elif isinstance(original_hotel_id, (int, str)):
                        try:
                            hotel_id_int = int(original_hotel_id)
                            hotel = (
                                request.env["hotel.hotels"].sudo().browse(hotel_id_int)
                            )
                            if hotel.exists():
                                room["hotel_id"] = [hotel_id_int, hotel.name]
                            else:
                                room["hotel_id"] = False
                        except (ValueError, TypeError):
                            room["hotel_id"] = False
                    else:
                        room["hotel_id"] = False
                else:
                    room["hotel_id"] = False

            first_day = target_date.replace(day=1)
            last_day = first_day + timedelta(days=31)

            domain = [
                ("check_in", "<=", datetime.combine(last_day, datetime.max.time())),
                ("check_out", ">=", datetime.combine(first_day, datetime.min.time())),
                ("status_bar", "not in", ["cancel", "cancelled", "room_ready"]),
            ]

            bookings = (
                request.env["hotel.booking"]
                .sudo()
                .search_read(
                    domain,
                    fields=[
                        "id",
                        "check_in",
                        "check_out",
                        "status_bar",
                        "partner_id",
                        "total_amount",
                        "currency_id",
                        "connected_booking_id",
                        "is_room_change_origin",
                        "is_room_change_destination",
                    ],
                    limit=1000,
                )
            )

            booking_ids = [b["id"] for b in bookings]
            booking_lines = (
                request.env["hotel.booking.line"]
                .sudo()
                .search_read(
                    [("booking_id", "in", booking_ids)],
                    fields=[
                        "id",
                        "booking_id",
                        "product_tmpl_id",
                        "booking_days",
                        "discount_reason",
                    ],
                )
            )

            lines_by_booking = {}
            for line in booking_lines:
                if line.get("booking_id"):
                    booking_id = line["booking_id"][0]
                    if booking_id not in lines_by_booking:
                        lines_by_booking[booking_id] = []
                    lines_by_booking[booking_id].append(line)

            reservations = []
            for booking in bookings:
                booking_id = booking.get("id")
                if booking_id and booking_id in lines_by_booking:
                    booking_check_in = booking.get("check_in")
                    booking_check_out = booking.get("check_out")

                    if not booking_check_in or not booking_check_out:
                        continue

                    try:
                        check_in_base = fields.Datetime.context_timestamp(
                            request.env.user, booking_check_in
                        )
                        check_out_base = fields.Datetime.context_timestamp(
                            request.env.user, booking_check_out
                        )
                    except:
                        check_in_base = booking_check_in
                        check_out_base = booking_check_out

                    booking_check_in_hour = None
                    booking_check_in_minute = None
                    booking_check_out_hour = None
                    booking_check_out_minute = None
                    booking_duration_hours = None
                    booking_duration_days = None

                    if isinstance(check_in_base, datetime):
                        booking_check_in_hour = check_in_base.hour
                        booking_check_in_minute = check_in_base.minute

                    if isinstance(check_out_base, datetime):
                        booking_check_out_hour = check_out_base.hour
                        booking_check_out_minute = check_out_base.minute

                        if isinstance(check_in_base, datetime):
                            duration_delta = check_out_base - check_in_base
                            booking_duration_hours = (
                                duration_delta.total_seconds() / 3600.0
                            )
                            booking_duration_days = duration_delta.days + (
                                duration_delta.seconds / 86400.0
                            )

                    lines = sorted(
                        lines_by_booking[booking_id], key=lambda x: x.get("id", 0)
                    )
                    current_date = check_in_base

                    has_room_changes = len(lines) > 1 and any(
                        line.get("product_tmpl_id") != lines[0].get("product_tmpl_id")
                        for line in lines[1:]
                        if line.get("product_tmpl_id")
                    )

                    for i, line in enumerate(lines):
                        if line.get("product_tmpl_id"):
                            booking_days = line.get("booking_days", 0)
                            if booking_days <= 0:
                                continue

                            if has_room_changes:
                                if i == 0:
                                    line_start = check_in_base
                                    line_end = check_in_base + timedelta(
                                        days=booking_days
                                    )
                                else:
                                    change_start = check_in_base + timedelta(
                                        days=sum(
                                            lines[j].get("booking_days", 0)
                                            for j in range(i)
                                        )
                                    )
                                    line_start = change_start
                                    line_end = change_start + timedelta(
                                        days=booking_days
                                    )
                            else:
                                line_start = current_date
                                line_end = current_date + timedelta(days=booking_days)
                                current_date = line_end

                            total_amount = booking.get("total_amount", 0.0)
                            currency_symbol = ""
                            if (
                                booking.get("currency_id")
                                and isinstance(booking["currency_id"], (list, tuple))
                                and len(booking["currency_id"]) > 1
                            ):
                                currency_symbol = booking["currency_id"][1]
                            elif (
                                booking.get("currency_id")
                                and isinstance(booking["currency_id"], (list, tuple))
                                and len(booking["currency_id"]) > 0
                            ):
                                try:
                                    currency = (
                                        request.env["res.currency"]
                                        .sudo()
                                        .browse(booking["currency_id"][0])
                                    )
                                    if currency.exists():
                                        currency_symbol = currency.symbol
                                except:
                                    currency_symbol = "$"
                            else:
                                currency_symbol = "$"

                            line_check_in_hour = None
                            line_check_in_minute = None
                            line_check_out_hour = None
                            line_check_out_minute = None
                            line_is_half_day_checkin = False
                            line_is_half_day_checkout = False
                            line_duration_hours = None
                            line_duration_days = None

                            if isinstance(line_start, datetime):
                                line_check_in_hour = line_start.hour
                                line_check_in_minute = line_start.minute
                                line_is_half_day_checkin = line_check_in_hour >= 12

                            if isinstance(line_end, datetime):
                                line_check_out_hour = line_end.hour
                                line_check_out_minute = line_end.minute
                                line_is_half_day_checkout = line_check_out_hour < 12

                                if isinstance(line_start, datetime):
                                    line_duration_delta = line_end - line_start
                                    line_duration_hours = (
                                        line_duration_delta.total_seconds() / 3600.0
                                    )
                                    line_duration_days = line_duration_delta.days + (
                                        line_duration_delta.seconds / 86400.0
                                    )

                            reservation_data = {
                                "id": line.get("id", 0),
                                "booking_id": booking_id or 0,
                                "date_start": (
                                    line_start.isoformat()
                                    if hasattr(line_start, "isoformat")
                                    else str(line_start)
                                ),
                                "date_end": (
                                    line_end.isoformat()
                                    if hasattr(line_end, "isoformat")
                                    else str(line_end)
                                ),
                                "state": booking.get("status_bar", ""),
                                "status_bar": booking.get("status_bar", ""),
                                "customer_name": (
                                    booking["partner_id"][1]
                                    if booking.get("partner_id")
                                    and booking["partner_id"]
                                    and len(booking["partner_id"]) > 1
                                    else "N/A"
                                ),
                                "partner_id": (
                                    booking["partner_id"][0]
                                    if booking.get("partner_id")
                                    and booking["partner_id"]
                                    and len(booking["partner_id"]) > 0
                                    else None
                                ),
                                "room_id": (
                                    [
                                        line["product_tmpl_id"][0],
                                        line["product_tmpl_id"][1],
                                    ]
                                    if line.get("product_tmpl_id")
                                    and line["product_tmpl_id"]
                                    and len(line["product_tmpl_id"]) > 1
                                    else [0, ""]
                                ),
                                "room_name": (
                                    line["product_tmpl_id"][1]
                                    if line.get("product_tmpl_id")
                                    and line["product_tmpl_id"]
                                    and len(line["product_tmpl_id"]) > 1
                                    else ""
                                ),
                                "total_amount": total_amount,
                                "currency_symbol": currency_symbol,
                                "discount_reason": line.get("discount_reason", "")
                                or "",
                                "check_in_hour": line_check_in_hour,
                                "check_in_minute": line_check_in_minute,
                                "check_out_hour": line_check_out_hour,
                                "check_out_minute": line_check_out_minute,
                                "is_half_day_checkin": line_is_half_day_checkin,
                                "is_half_day_checkout": line_is_half_day_checkout,
                                "duration_hours": (
                                    round(line_duration_hours, 2)
                                    if line_duration_hours is not None
                                    else None
                                ),
                                "duration_days": (
                                    round(line_duration_days, 2)
                                    if line_duration_days is not None
                                    else None
                                ),
                                "booking_check_in": (
                                    booking_check_in.isoformat()
                                    if isinstance(booking_check_in, datetime)
                                    else str(booking_check_in)
                                ),
                                "booking_check_out": (
                                    booking_check_out.isoformat()
                                    if isinstance(booking_check_out, datetime)
                                    else str(booking_check_out)
                                ),
                                "booking_check_in_hour": booking_check_in_hour,
                                "booking_check_in_minute": booking_check_in_minute,
                                "booking_check_out_hour": booking_check_out_hour,
                                "booking_check_out_minute": booking_check_out_minute,
                                "booking_duration_hours": (
                                    round(booking_duration_hours, 2)
                                    if booking_duration_hours is not None
                                    else None
                                ),
                                "booking_duration_days": (
                                    round(booking_duration_days, 2)
                                    if booking_duration_days is not None
                                    else None
                                ),
                            }

                            if has_room_changes:
                                reservation_data["is_room_change"] = True
                            else:
                                reservation_data["is_new_reservation"] = True

                            if booking.get("connected_booking_id"):
                                reservation_data["connected_booking_id"] = (
                                    booking["connected_booking_id"][0]
                                    if isinstance(
                                        booking["connected_booking_id"], (list, tuple)
                                    )
                                    else booking["connected_booking_id"]
                                )
                                reservation_data["is_room_change_origin"] = booking.get(
                                    "is_room_change_origin", False
                                )
                                reservation_data["is_room_change_destination"] = (
                                    booking.get("is_room_change_destination", False)
                                )

                            reservations.append(reservation_data)

            if target_date.month == 12:
                last_day_month = target_date.replace(
                    year=target_date.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                last_day_month = target_date.replace(
                    month=target_date.month + 1, day=1
                ) - timedelta(days=1)

            days = list(range(1, last_day_month.day + 1))

            month_info = {
                "month_name": target_date.strftime("%B %Y").title(),
                "month_number": target_date.month,
                "year": target_date.year,
                "days": days,
                "first_day": first_day.isoformat(),
                "last_day": last_day_month.isoformat(),
                "total_days": len(days),
            }

            metadata = {
                "total_rooms": len(rooms),
                "total_reservations": len(reservations),
                "hotel_id": hotel_id,
                "target_date": target_date.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "timezone": str(request.env.user.tz) if request.env.user.tz else "UTC",
            }

            return self._prepare_response(
                {
                    "success": True,
                    "data": {
                        "rooms": rooms,
                        "reservations": reservations,
                        "month_info": month_info,
                        "metadata": metadata,
                    },
                }
            )

        except Exception as e:
            _logger.exception("Error obteniendo datos del Gantt: %s", str(e))
            return self._prepare_response(
                {"success": False, "error": str(e)}, status=500
            )
