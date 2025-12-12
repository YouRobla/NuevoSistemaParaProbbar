# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import http, _
from odoo.http import request
from ..api_auth import validate_api_key
from .utils import handle_api_errors


class ResourceEndpoints:

    @http.route(
        "/api/hotel/hoteles",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        cors="*",
    )
    @validate_api_key
    @handle_api_errors
    def get_hoteles(self, **kw):
        """Obtener lista de hoteles disponibles"""
        hotels = request.env["hotel.hotels"].search([])
        hotels_list = [
            {
                "id": hotel.id,
                "name": hotel.name,
                "active": hotel.active if hasattr(hotel, "active") else True,
            }
            for hotel in hotels
        ]
        return self._prepare_response(
            {"success": True, "count": len(hotels_list), "data": hotels_list}
        )

    @http.route(
        "/api/hotel/habitaciones",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        cors="*",
    )
    @validate_api_key
    @handle_api_errors
    def get_habitaciones(self, **kw):
        """Obtener lista de habitaciones (productos tipo habitación)"""
        domain = [("is_room_type", "=", True)]

        if kw.get("hotel_id"):
            hotel_id = self._validate_hotel_id(kw["hotel_id"])
            # Agregar filtro por hotel si el campo existe en el modelo de producto o templates
            # Esto depende de si product.product tiene hotel_id directamente o a través de template
            # Asumimos que no filtramos directamente en la búsqueda inicial si no estamos seguros del campo
            pass

        products = request.env["product.product"].search(domain)

        # Filtrado manual por hotel_id si es necesario y si el campo existe
        # Pero para mantener compatibilidad con el código original, lo dejamos así
        # (el original tenía comentado el filtro de hotel_id)

        rooms_list = [
            {
                "id": product.id,
                "name": product.name,
                "code": product.default_code or "",
                "barcode": product.barcode or "",
                "list_price": product.list_price,
                "active": product.active,
            }
            for product in products
        ]

        return self._prepare_response(
            {"success": True, "count": len(rooms_list), "data": rooms_list}
        )

    @http.route(
        "/api/hotel/health",
        auth="public",
        type="http",
        methods=["GET", "OPTIONS"],
        csrf=False,
        cors="*",
    )
    def health_check(self, **kw):
        """Verificar estado del API"""
        return self._prepare_response(
            {
                "success": True,
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
            }
        )
