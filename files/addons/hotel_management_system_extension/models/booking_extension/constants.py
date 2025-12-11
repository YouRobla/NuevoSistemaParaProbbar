# -*- coding: utf-8 -*-
from odoo import _


class BookingState:
    """Clase para definir constantes de estados - Compatible con XML"""

    # Estados principales
    INITIAL = "initial"
    CONFIRMED = "confirmed"
    CHECKIN = "checkin"
    CHECKOUT = "checkout"
    CLEANING_NEEDED = "cleaning_needed"
    ROOM_READY = "room_ready"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

    # Estados legacy (compatibilidad con módulo base)
    DRAFT = "draft"
    ALLOT = "allot"
    CHECK_IN = "check_in"
    PENDING = "pending"
    CHECKOUT_PENDING = "checkout_pending"


# Definición de estados con metadatos
BOOKING_STATES = {
    BookingState.INITIAL: {
        "name": "Borrador",
        "description": "Reserva en estado inicial",
        "color": "secondary",
        "is_terminal": False,
        "requires_room": False,
    },
    BookingState.CONFIRMED: {
        "name": "Confirmada",
        "description": "Reserva confirmada por el cliente",
        "color": "info",
        "is_terminal": False,
        "requires_room": False,
    },
    BookingState.CHECKIN: {
        "name": "Check-in Realizado",
        "description": "Huésped en la habitación",
        "color": "success",
        "is_terminal": False,
        "requires_room": True,
    },
    BookingState.CHECKOUT: {
        "name": "Check-out Realizado",
        "description": "Huésped ha salido",
        "color": "primary",
        "is_terminal": False,
        "requires_room": True,
    },
    BookingState.CLEANING_NEEDED: {
        "name": "Limpieza Necesaria",
        "description": "Habitación requiere limpieza",
        "color": "warning",
        "is_terminal": False,
        "requires_room": True,
    },
    BookingState.ROOM_READY: {
        "name": "Habitación Lista",
        "description": "Habitación lista para nuevo huésped",
        "color": "success",
        "is_terminal": False,
        "requires_room": True,
    },
    BookingState.CANCELLED: {
        "name": "Cancelada",
        "description": "Reserva cancelada",
        "color": "danger",
        "is_terminal": True,
        "requires_room": False,
    },
    BookingState.NO_SHOW: {
        "name": "No Se Presentó",
        "description": "Cliente no se presentó",
        "color": "danger",
        "is_terminal": True,
        "requires_room": False,
    },
    # Estados legacy
    BookingState.DRAFT: {
        "name": "Borrador",
        "description": "Estado borrador legacy",
        "color": "secondary",
        "is_terminal": False,
        "requires_room": False,
    },
    BookingState.ALLOT: {
        "name": "Habitación Asignada",
        "description": "Habitación asignada (legacy)",
        "color": "warning",
        "is_terminal": False,
        "requires_room": True,
    },
    BookingState.CHECK_IN: {
        "name": "Check-in Legacy",
        "description": "Check-in legacy",
        "color": "success",
        "is_terminal": False,
        "requires_room": True,
    },
}

# Reglas de transición optimizadas (compatible con XML)
STATE_TRANSITIONS = {
    BookingState.INITIAL: [BookingState.CONFIRMED, BookingState.CANCELLED],
    BookingState.CONFIRMED: [
        BookingState.CHECKIN,
        BookingState.CANCELLED,
        BookingState.NO_SHOW,
    ],
    BookingState.CHECKIN: [BookingState.CHECKOUT, BookingState.CANCELLED],
    BookingState.CHECKOUT: [BookingState.CLEANING_NEEDED],
    BookingState.CLEANING_NEEDED: [BookingState.ROOM_READY],
    BookingState.ROOM_READY: [BookingState.CONFIRMED],  # Para reutilizar habitación
    BookingState.CANCELLED: [BookingState.INITIAL],  # Permitir reactivar
    BookingState.NO_SHOW: [BookingState.INITIAL],  # Permitir reactivar
    # Estados legacy (compatibilidad)
    BookingState.DRAFT: [BookingState.CONFIRMED, BookingState.CANCELLED],
    BookingState.ALLOT: [
        BookingState.CHECKIN,
        BookingState.CANCELLED,
        BookingState.NO_SHOW,
    ],
    BookingState.CHECK_IN: [BookingState.CHECKOUT, BookingState.CANCELLED],
    BookingState.PENDING: [BookingState.CONFIRMED, BookingState.CANCELLED],
}
