# -*- coding: utf-8 -*-
"""
Controlador para creación batch de reservas.
Maneja múltiples segmentos y detecta automáticamente si son consecutivos.
"""
from odoo import http
from odoo.http import request, Response
from odoo.tools import json_default
import json
import logging
from datetime import datetime
from .api_auth import validate_api_key

_logger = logging.getLogger(__name__)


class BatchReservationsController(http.Controller):
    """
    Controlador para crear múltiples reservas de forma inteligente.
    
    Endpoint: POST /api/hotel/reservas/batch
    
    Payload:
    {
        "partner_id": 123,
        "user_id": 456,
        "hotel_id": 1,
        "motivo_viaje": "Negocios",
        "segments": [
            {
                "room_id": 101,
                "check_in": "2024-01-15 14:00:00",
                "check_out": "2024-01-17 10:00:00",
                "guests": [
                    {"name": "Juan", "age": 30, "gender": "male"}
                ]
            }
        ]
    }
    """

    def _prepare_response(self, data, status=200):
        """Preparar respuesta HTTP con formato JSON y headers CORS"""
        return Response(
            json.dumps(data, default=json_default, ensure_ascii=False),
            status=status,
            content_type='application/json',
            headers={

                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
            }
        )

    def _cors_response(self):
        """Respuesta para preflight OPTIONS."""
        return Response(
            '',
            headers={

                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
                'Access-Control-Max-Age': '86400',
            },
            status=200
        )

    @http.route('/api/hotel/reservas/batch', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @validate_api_key
    def create_batch_reservations(self, **kwargs):
        """
        Crea múltiples reservas vinculadas mediante change_room.
        
        IMPORTANTE: TODOS los segmentos se vinculan entre sí, sin importar
        cuántos días haya entre ellos. Esto permite crear reservas con gaps
        (ej: 15-17 Enero, 25-27 Enero) que quedan conectadas.
        """
        # Manejar preflight OPTIONS
        if request.httprequest.method == 'OPTIONS':
            return self._cors_response()

        # Parsear datos
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        except Exception as e:
            _logger.error(f"❌ Error parsing JSON: {e}")
            return self._prepare_response({
                'success': False,
                'error': 'Invalid JSON format'
            }, status=400)

        # Validar campos requeridos
        required_fields = ['partner_id', 'user_id', 'hotel_id', 'segments']
        for field in required_fields:
            if field not in data:
                return self._prepare_response({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }, status=400)

        if not isinstance(data['segments'], list) or len(data['segments']) == 0:
            return self._prepare_response({
                'success': False,
                'error': 'segments must be a non-empty array'
            }, status=400)

        # Procesar reservas
        try:
            _logger.info(f"📥 Batch request: {len(data['segments'])} segments")
            result = self._process_batch_reservations(data)
            _logger.info(f"✅ Batch completed: {result['message']}")

            return self._prepare_response(result)

        except Exception as e:
            _logger.error(f"❌ Error processing batch: {e}", exc_info=True)
            return self._prepare_response({
                'success': False,
                'error': str(e)
            }, status=500)

    def _process_batch_reservations(self, data):
        """
        Lógica principal para procesar múltiples reservas.
        """
        partner_id = data['partner_id']
        user_id = data['user_id']
        hotel_id = data['hotel_id']
        motivo_viaje = data.get('motivo_viaje', '')
        segments = data['segments']

        # 1. Analizar consecutividad
        groups = self._analyze_segments(segments)
        _logger.info(f"📊 Detected {len(groups)} groups")

        # 2. Crear reservas según grupos
        created_reservations = []

        for idx, group in enumerate(groups):
            _logger.info(f"🔄 Processing group {idx + 1}/{len(groups)}: {group['type']}")

            if group['type'] == 'consecutive':
                # Usar estrategia de change_room para mantener vinculadas
                reservations = self._create_consecutive_group(
                    group['segments'],
                    partner_id,
                    user_id,
                    hotel_id,
                    motivo_viaje
                )
                created_reservations.extend(reservations)
            else:
                # Crear reservas separadas
                for segment in group['segments']:
                    reservation = self._create_single_reservation(
                        segment,
                        partner_id,
                        user_id,
                        hotel_id,
                        motivo_viaje
                    )
                    created_reservations.append(reservation)

        return {
            'success': True,
            'message': f'{len(created_reservations)} reservas creadas exitosamente',
            'data': {
                'reservations': [self._serialize_reservation(r) for r in created_reservations],
                'groups': groups,
                'total_created': len(created_reservations)
            }
        }

    def _analyze_segments(self, segments):
        """
        Analiza los segmentos - SIEMPRE los trata como un grupo vinculado.
        
        No importa cuántos días haya entre segmentos, todos se vinculan.
        
        Returns:
            [
                {
                    'type': 'consecutive',
                    'segments': [seg1, seg2, seg3, ...],
                    'count': N
                }
            ]
        """
        # SIEMPRE retornar todos los segmentos como UN SOLO grupo consecutivo
        return [{
            'type': 'consecutive',
            'segments': segments,
            'count': len(segments)
        }]

    def _parse_datetime(self, dt_str):
        """Parsea string a datetime con múltiples formatos"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Could not parse datetime: {dt_str}")

    def _create_consecutive_group(self, segments, partner_id, user_id, hotel_id, motivo_viaje):
        """
        Crea un grupo de reservas vinculadas.
        
        NUEVA ESTRATEGIA:
        1. Crear cada reserva con sus propias fechas (no una maestra grande)
        2. Vincularlas mediante split_from_booking_id y connected_booking_id
        3. Cada reserva aparece como segmento individual en el calendario
        """
        Booking = request.env['hotel.booking'].sudo()
        partner = request.env['res.partner'].sudo().browse(partner_id)
        
        created_reservations = []
        previous_booking = None
        
        # Crear cada segmento como reserva individual
        for idx, segment in enumerate(segments):
            _logger.info(f"🏨 Creating booking {idx + 1}/{len(segments)}: {segment['check_in']} → {segment['check_out']}")
            
            # Preparar datos de huéspedes
            guest_commands = self._create_guests(segment.get('guests', []))
            if not guest_commands:
                guest_commands = [(0, 0, {
                    'name': partner.name or 'Huésped',
                    'age': 30,
                    'gender': 'other',
                    'partner_id': partner_id,
                })]
            
            # Convertir strings de fecha a datetime para evitar conversión UTC
            check_in_dt = self._parse_datetime(segment['check_in'])
            check_out_dt = self._parse_datetime(segment['check_out'])
            
            # Preparar valores de la reserva
            booking_vals = {
                'partner_id': partner_id,
                'user_id': user_id,
                'hotel_id': hotel_id,
                'check_in': check_in_dt,  # Datetime naive → Sin conversión UTC
                'check_out': check_out_dt,  # Datetime naive → Sin conversión UTC
                'motivo_viaje': motivo_viaje,
                'status_bar': 'initial',
                'booking_line_ids': [(0, 0, {
                    'product_id': segment['room_id'],
                    'guest_info_ids': guest_commands,
                })]
            }
            
            # Si no es la primera, vincular con la anterior
            if previous_booking:
                booking_vals['split_from_booking_id'] = previous_booking.id
                booking_vals['is_room_change_destination'] = True
            else:
                # La primera es el origen
                booking_vals['is_room_change_origin'] = True
            
            # Crear la reserva
            current_booking = Booking.create(booking_vals)
            _logger.info(f"✅ Booking created: {current_booking.id} - {current_booking.sequence_id}")
            
            # Actualizar la reserva anterior para que apunte a esta
            if previous_booking:
                previous_booking.write({
                    'connected_booking_id': current_booking.id,
                    'is_room_change_origin': True,
                })
                _logger.info(f"🔗 Linked {previous_booking.sequence_id} → {current_booking.sequence_id}")
            
            created_reservations.append(current_booking)
            previous_booking = current_booking
        
        _logger.info(f"✅ Created {len(created_reservations)} linked reservations")
        return created_reservations

    def _create_single_reservation(self, segment, partner_id, user_id, hotel_id, motivo_viaje):
        """
        Crea una reserva individual.
        """
        Booking = request.env['hotel.booking'].sudo()
        partner = request.env['res.partner'].sudo().browse(partner_id)

        _logger.info(f"🏨 Creating single booking: {segment['check_in']} → {segment['check_out']}")

        # Preparar datos de huéspedes
        guest_commands = self._create_guests(segment.get('guests', []))
        if not guest_commands:
            guest_commands = [(0, 0, {
                'name': partner.name or 'Huésped',
                'age': 30,
                'gender': 'other',
                'partner_id': partner_id,
            })]

        # Convertir strings de fecha a datetime para evitar conversión UTC
        check_in_dt = self._parse_datetime(segment['check_in'])
        check_out_dt = self._parse_datetime(segment['check_out'])

        booking = Booking.create({
            'partner_id': partner_id,
            'user_id': user_id,
            'hotel_id': hotel_id,
            'check_in': check_in_dt,  # Datetime naive → Sin conversión UTC
            'check_out': check_out_dt,  # Datetime naive → Sin conversión UTC
            'motivo_viaje': motivo_viaje,
            'status_bar': 'initial',
            'booking_line_ids': [(0, 0, {
                'product_id': segment['room_id'],
                'guest_info_ids': guest_commands,
            })]
        })

        _logger.info(f"✅ Single booking created: {booking.id} - {booking.sequence_id}")
        return booking

    def _create_guests(self, guests_data):
        """
        Crea comandos para guest_info_ids.
        """
        if not guests_data:
            return []

        commands = []
        for guest in guests_data:
            guest_vals = {
                'name': guest.get('name', 'Guest'),
                'age': guest.get('age', 30),
                'gender': guest.get('gender', 'other'),
            }
            if guest.get('partner_id'):
                guest_vals['partner_id'] = guest['partner_id']
            commands.append((0, 0, guest_vals))

        return commands

    def _serialize_reservation(self, booking):
        """
        Serializa una reserva para la respuesta JSON.
        """
        rooms = []
        for line in booking.booking_line_ids:
            rooms.append({
                'id': line.product_id.id if line.product_id else None,
                'name': line.product_id.name if line.product_id else '',
            })

        return {
            'id': booking.id,
            'sequence_id': booking.sequence_id or '',
            'check_in': booking.check_in.strftime('%Y-%m-%d %H:%M:%S') if booking.check_in else '',
            'check_out': booking.check_out.strftime('%Y-%m-%d %H:%M:%S') if booking.check_out else '',
            'status_bar': booking.status_bar or 'initial',
            'total_amount': float(booking.total_amount) if booking.total_amount else 0.0,
            'partner_id': booking.partner_id.id if booking.partner_id else None,
            'partner_name': booking.partner_id.name if booking.partner_id else '',
            'hotel_id': booking.hotel_id.id if booking.hotel_id else None,
            'hotel_name': booking.hotel_id.name if booking.hotel_id else '',
            'rooms': rooms,
            'has_room_change': getattr(booking, 'has_room_change', False),
            'split_from_booking_id': booking.split_from_booking_id.id if booking.split_from_booking_id else None,
            'connected_booking_id': booking.connected_booking_id.id if getattr(booking, 'connected_booking_id', None) else None,
        }
