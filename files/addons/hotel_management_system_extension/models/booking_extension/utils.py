# -*- coding: utf-8 -*-
from odoo import fields, _
from datetime import datetime
from .constants import BookingState, BOOKING_STATES, STATE_TRANSITIONS


class StateTransitionValidator:
    """Clase para validar transiciones de estado"""

    @staticmethod
    def is_valid_transition(current_state, new_state):
        """Validar si una transición es permitida"""
        allowed_transitions = STATE_TRANSITIONS.get(current_state, [])
        return new_state in allowed_transitions

    @staticmethod
    def get_available_transitions(current_state):
        """Obtener transiciones disponibles"""
        return STATE_TRANSITIONS.get(current_state, [])

    @staticmethod
    def validate_transition_rules(booking, new_state):
        """Validar reglas específicas para transiciones"""
        errors = []

        # Validar habitación asignada
        state_info = BOOKING_STATES.get(new_state, {})
        if state_info.get("requires_room", False) and not booking.booking_line_ids:
            errors.append(
                _('Se requiere habitación asignada para el estado "%s"')
                % state_info.get("name", new_state)
            )

        # Validar fechas para check-in
        if new_state == BookingState.CHECKIN:
            today = fields.Date.today()
            checkin_date = booking.check_in
            if checkin_date:
                # Manejo robusto de fechas para Odoo 17
                if isinstance(checkin_date, datetime):
                    checkin_date_obj = checkin_date.date()
                elif isinstance(checkin_date, str):
                    checkin_date_obj = fields.Date.from_string(checkin_date)
                else:
                    checkin_date_obj = checkin_date

                if checkin_date_obj and checkin_date_obj > today:
                    errors.append(
                        _("No se puede realizar check-in antes de la fecha programada")
                    )

        # Validar fechas para check-out
        if new_state == BookingState.CHECKOUT:
            if not booking.check_out:
                errors.append(_("Debe especificar la fecha de check-out"))

        return errors
