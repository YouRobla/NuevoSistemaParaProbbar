# -*- coding: utf-8 -*-
import json
import logging
from functools import wraps
from odoo import http
from odoo.http import request, Response
from odoo.tools import json_default
from odoo.exceptions import AccessError, ValidationError, UserError
from .api_auth import validate_api_key

_logger = logging.getLogger(__name__)


def handle_exceptions(func):
    """Decorador para manejo centralizado de excepciones."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except AccessError as e:
            _logger.warning(f"Error de acceso en {func.__name__}: {str(e)}")
            return self._error_response(
                'No tiene permisos para acceder a esta información',
                status=403
            )
        except ValidationError as e:
            _logger.error(f"Error de validación en {func.__name__}: {str(e)}")
            return self._error_response(
                f'Error de validación: {str(e)}',
                status=400
            )
        except Exception as e:
            _logger.exception(f"Error inesperado en {func.__name__}: {str(e)}")
            return self._error_response(
                'Error interno del servidor',
                status=500
            )
    return wrapper


class HotelStatesAPIController(http.Controller):
    """
    API REST para gestión de estados del sistema hotelero en Odoo 17.
    
    Proporciona endpoints para consultar estados y transiciones de:
    - hotel.booking: Estados de reservas
    - hotel.housekeeping: Estados de mantenimiento
    
    Módulos relacionados:
    - hotel_management_system (Hotel/)
    - hotel_management_system_extension (ConsultingERP/)
    """

    # Definición centralizada de estados de booking
    BOOKING_STATES = [
        {
            'code': 'initial',
            'name': 'Borrador',
            'name_en': 'Draft',
            'description': 'Reserva en estado inicial, pendiente de confirmación',
            'color': 'secondary',
            'hex_color': '#6c757d',
            'icon': 'fa-file-text-o',
            'is_terminal': False,
            'requires_room': False,
            'requires_payment': False,
            'next_states': ['confirmed', 'cancelled'],
            'order': 1
        },
        {
            'code': 'confirmed',
            'name': 'Confirmada',
            'name_en': 'Confirmed',
            'description': 'Reserva confirmada por el cliente, en espera de check-in',
            'color': 'info',
            'hex_color': '#17a2b8',
            'icon': 'fa-check-circle',
            'is_terminal': False,
            'requires_room': False,
            'requires_payment': True,
            'next_states': ['checkin', 'cancelled', 'no_show'],
            'order': 2
        },
        {
            'code': 'checkin',
            'name': 'Check-in Realizado',
            'name_en': 'Checked In',
            'description': 'Huésped registrado y ocupando la habitación',
            'color': 'success',
            'hex_color': '#28a745',
            'icon': 'fa-sign-in',
            'is_terminal': False,
            'requires_room': True,
            'requires_payment': True,
            'next_states': ['checkout', 'cancelled'],
            'order': 3
        },
        {
            'code': 'checkout',
            'name': 'Check-out Realizado',
            'name_en': 'Checked Out',
            'description': 'Huésped ha finalizado su estancia',
            'color': 'primary',
            'hex_color': '#007bff',
            'icon': 'fa-sign-out',
            'is_terminal': False,
            'requires_room': True,
            'requires_payment': True,
            'next_states': ['cleaning_needed'],
            'order': 4
        },
        {
            'code': 'cleaning_needed',
            'name': 'Limpieza Necesaria',
            'name_en': 'Cleaning Needed',
            'description': 'Habitación requiere limpieza y preparación',
            'color': 'warning',
            'hex_color': '#ffc107',
            'icon': 'fa-broom',
            'is_terminal': False,
            'requires_room': True,
            'requires_payment': False,
            'next_states': ['room_ready'],
            'order': 5
        },
        {
            'code': 'room_ready',
            'name': 'Habitación Lista',
            'name_en': 'Room Ready',
            'description': 'Habitación limpia y lista para nuevo huésped',
            'color': 'success',
            'hex_color': '#28a745',
            'icon': 'fa-thumbs-up',
            'is_terminal': False,
            'requires_room': True,
            'requires_payment': False,
            'next_states': ['confirmed'],
            'order': 6
        },
        {
            'code': 'cancelled',
            'name': 'Cancelada',
            'name_en': 'Cancelled',
            'description': 'Reserva cancelada por el cliente o el sistema',
            'color': 'danger',
            'hex_color': '#dc3545',
            'icon': 'fa-times-circle',
            'is_terminal': True,
            'requires_room': False,
            'requires_payment': False,
            'next_states': ['initial'],
            'can_reactivate': True,
            'order': 7
        },
        {
            'code': 'no_show',
            'name': 'No Se Presentó',
            'name_en': 'No Show',
            'description': 'Cliente no se presentó en la fecha programada',
            'color': 'danger',
            'hex_color': '#dc3545',
            'icon': 'fa-user-times',
            'is_terminal': True,
            'requires_room': False,
            'requires_payment': False,
            'next_states': ['initial'],
            'can_reactivate': True,
            'order': 8
        }
    ]

    # Definición centralizada de estados de housekeeping
    HOUSEKEEPING_STATES = [
        {
            'code': 'draft',
            'name': 'Borrador',
            'name_en': 'Draft',
            'description': 'Tarea de mantenimiento programada, pendiente de inicio',
            'color': 'secondary',
            'hex_color': '#6c757d',
            'icon': 'fa-clock-o',
            'is_terminal': False,
            'next_states': ['in_progress'],
            'order': 1
        },
        {
            'code': 'in_progress',
            'name': 'En Progreso',
            'name_en': 'In Progress',
            'description': 'Mantenimiento o limpieza en curso',
            'color': 'warning',
            'hex_color': '#ffc107',
            'icon': 'fa-spinner',
            'is_terminal': False,
            'next_states': ['completed', 'draft'],
            'order': 2
        },
        {
            'code': 'completed',
            'name': 'Completado',
            'name_en': 'Completed',
            'description': 'Mantenimiento finalizado, habitación verificada',
            'color': 'success',
            'hex_color': '#28a745',
            'icon': 'fa-check-square',
            'is_terminal': True,
            'next_states': [],
            'order': 3
        }
    ]

    def _prepare_response(self, data, status=200):
        """
        Prepara respuesta HTTP JSON.
        
        Args:
            data (dict): Datos a serializar
            status (int): Código HTTP
            
        Returns:
            Response: Respuesta HTTP configurada
        """
        return Response(
            json.dumps(data, default=json_default, ensure_ascii=False),
            status=status,
            content_type='application/json; charset=utf-8',
        )

    def _success_response(self, data, message=None, **kwargs):
        """Respuesta exitosa estandarizada."""
        response_data = {
            'success': True,
            'data': data,
            'timestamp': json_default(request.env.cr.now())
        }
        if message:
            response_data['message'] = message
        response_data.update(kwargs)
        return self._prepare_response(response_data)

    def _error_response(self, error, status=400, code=None):
        """Respuesta de error estandarizada."""
        return self._prepare_response({
            'success': False,
            'error': error,
            'code': code or f'ERROR_{status}',
            'timestamp': json_default(request.env.cr.now())
        }, status=status)

    def _get_state_transitions_graph(self, state_type='booking'):
        """
        Genera un grafo de transiciones de estados.
        
        Args:
            state_type (str): Tipo de estado ('booking' o 'housekeeping')
            
        Returns:
            dict: Grafo de transiciones
        """
        states = self.BOOKING_STATES if state_type == 'booking' else self.HOUSEKEEPING_STATES
        
        graph = {}
        for state in states:
            graph[state['code']] = {
                'name': state['name'],
                'can_transition_to': state.get('next_states', []),
            }
        
        return graph