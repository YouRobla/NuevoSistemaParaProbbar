# -*- coding: utf-8 -*-
from odoo import http
from .main.utils import HotelApiUtils
from .main.serializers import HotelApiSerializers
from .main.booking_endpoints import BookingEndpoints
from .main.operation_endpoints import OperationEndpoints
from .main.resource_endpoints import ResourceEndpoints
from .main.gantt_endpoints import GanttEndpoints


class HotelApiController(
    http.Controller,
    HotelApiUtils,
    HotelApiSerializers,
    BookingEndpoints,
    OperationEndpoints,
    ResourceEndpoints,
    GanttEndpoints,
):
    """
    Controlador principal que agrupa toda la funcionalidad del API Hotelero.
    Refactorizado para mejorar mantenibilidad y modularidad.

    Estructura:
    - HotelApiUtils: Utilidades generales y manejo de errores
    - HotelApiSerializers: Serialización y validación de datos
    - BookingEndpoints: CRUD de reservas
    - OperationEndpoints: Operaciones sobre reservas (email, pagos, habitaciones, huéspedes)
    - ResourceEndpoints: Listados de recursos (hoteles, habitaciones)
    - GanttEndpoints: Datos para vista Gantt
    """

    pass
