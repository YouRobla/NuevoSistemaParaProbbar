# -*- coding: utf-8 -*-
import base64
import json

from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import UserError
from odoo.tools import json_default
from .api_auth import validate_api_key


class AdvancePaymentApiController(http.Controller):
    """
    Endpoints auxiliares para soportar el modal de pagos adelantados en el frontend.
    """

    def _parse_json_body(self):
        raw = request.httprequest.data
        if not raw:
            return {}
        try:
            return json.loads(raw.decode('utf-8'))
        except json.JSONDecodeError as exc:
            raise UserError(f'Formato JSON inválido: {exc}')

    def _prepare_response(self, data, status=200):
        """Preparar respuesta HTTP con formato JSON"""
        return Response(
            json.dumps(data, default=json_default),
            status=status,
            content_type='application/json'
        )

    @http.route(
        '/api/hotel/reserva/<int:booking_id>/advance_payment/options',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        website=False
    )
    @validate_api_key
    def get_advance_payment_options(self, booking_id):
        """
        Retorna los valores predeterminados y las opciones disponibles para el modal
        de registro de pago (advance payment) basado en la reserva indicada.
        """
        booking = request.env['hotel.booking'].browse(booking_id)
        if not booking.exists():
            return self._prepare_response({
                'success': False,
                'error': 'La reserva solicitada no existe.'
            }, status=404)

        sale_order = booking.order_id
        if not sale_order:
            return self._prepare_response({
                'success': False,
                'error': 'La reserva no tiene una orden de venta asociada.'
            }, status=400)

        company = sale_order.company_id or request.env.company

        amount = max(sale_order.amount_total - sale_order.paid_amount, 0.0)

        journal_domain = [
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', company.id),
        ]
        journals = request.env['account.journal'].search(journal_domain)
        journal_options = [
            {
                'value': journal.id,
                'label': journal.display_name,
                'code': journal.code,
                'type': journal.type,
            }
            for journal in journals
        ]

        payment_type = 'inbound'
        default_journal = journals[:1]
        if default_journal:
            if payment_type == 'inbound':
                available_method_lines = default_journal.inbound_payment_method_line_ids
            else:
                available_method_lines = default_journal.outbound_payment_method_line_ids
        else:
            available_method_lines = request.env['account.payment.method.line']

        payment_method_options = [
            {
                'value': line.id,
                'label': line.name,
                'code': line.payment_method_id.code,
                'method_type': line.payment_method_id.payment_type,
            }
            for line in available_method_lines
        ]

        payment_type_field_info = request.env['account.payment'].fields_get(['payment_type']).get('payment_type', {})
        selection = payment_type_field_info.get('selection', [])
        payment_type_options = [
            {'value': value, 'label': label}
            for value, label in selection
        ]

        response_payload = {
            'success': True,
            'data': {
                'defaults': {
                    'amount': amount,
                    'payment_type': payment_type,
                    'payment_date': fields.Date.context_today(request.env.user),
                    'journal_id': default_journal.id if default_journal else None,
                    'journal_name': default_journal.display_name if default_journal else None,
                    'payment_method_line_id': available_method_lines[:1].id if available_method_lines else None,
                    'payment_method_line_name': available_method_lines[:1].name if available_method_lines else None,
                    'currency': {
                        'id': sale_order.currency_id.id,
                        'name': sale_order.currency_id.name,
                        'symbol': sale_order.currency_id.symbol,
                    },
                    'partner': {
                        'id': sale_order.partner_id.id,
                        'name': sale_order.partner_id.display_name,
                    },
                    'company': {
                        'id': company.id,
                        'name': company.name,
                    },
                    'sale_order_id': sale_order.id,
                    'sale_order_name': sale_order.name,
                },
                'payment_type_options': payment_type_options,
                'journal_options': journal_options,
                'payment_method_options': payment_method_options,
            }
        }

        return self._prepare_response(response_payload)

    @http.route(
        '/api/hotel/reserva/<int:booking_id>/print_bill',
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        cors='*',
        csrf=False,
        website=False
    )
    @validate_api_key
    def print_reservation_bill(self, booking_id):
        """
        Devolver el recibo de la reserva (formato HTML/Ticket) 
        para impresión tipo POS.
        """
        booking = request.env['hotel.booking'].browse(booking_id)

        if not booking.exists():
            return self._prepare_response({'error': 'La reserva solicitada no existe.'}, status=404)

        # Renderizar el reporte "report_booking_receipt" (que ya existe)
        # Esto genera un HTML listo para imprimir.
        try:
            report_html = request.env['ir.actions.report']._render_qweb_html(
                'aac_hotel_api.report_booking_receipt', [booking.id]
            )[0]
            
            # Retornar el HTML en un JSON, o directamente HTML si prefieres.
            # Aquí lo envolvemos en JSON para consistencia con la API.
            return self._prepare_response({
                'success': True,
                'html': report_html.decode('utf-8') if isinstance(report_html, bytes) else report_html
            }, status=200)
        except Exception as e:
            return self._prepare_response({'error': f'Error generando recibo: {str(e)}'}, status=500)

    @http.route(
        '/api/hotel/reserva/<int:booking_id>/create_invoice',
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        cors='*',
        csrf=False,
        website=False
    )
    @validate_api_key
    def create_reservation_invoice(self, booking_id):
        """
        Crear la factura asociada a la reserva (equivalente al botón Create Invoice).
        Requiere que la reserva esté en estado 'room_ready', 'checkin' o 'checkout' 
        y no esté cancelada ni en borrador.
        """
        try:
            booking = request.env['hotel.booking'].browse(booking_id)
            if not booking.exists():
                return self._prepare_response({'error': 'Reserva no encontrada'}, status=404)

            # Llama al método nativo que crea la factura
            # Este método generalmente devuelve un diccionario de acción (tipo ir.actions.act_window)
            action_result = booking.create_invoice()

            # Buscar la factura recién creada vinculada a la reserva
            # Normalmente booking.invoice_ids contiene las facturas
            invoices = booking.order_id.invoice_ids if booking.order_id else request.env['account.move']
            
            invoice_data = []
            for inv in invoices:
                invoice_data.append({
                    'id': inv.id,
                    'name': inv.name,
                    'state': inv.state,
                    'amount_total': inv.amount_total
                })

            return self._prepare_response({
                'success': True,
                'message': 'Factura creada/actualizada correctamente.',
                'invoices': invoice_data,
                'action_debug': str(action_result)  # Opcional, para debug
            }, status=200)

        except Exception as e:
            return self._prepare_response({'error': str(e)}, status=500)

    @http.route(
        '/api/hotel/reserva/<int:booking_id>/mark_room_ready',
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        cors='*',
        csrf=False,
        website=False
    )
    @validate_api_key
    def mark_room_ready(self, booking_id):
        """
        Ejecutar el flujo de 'Habitación Lista' (action_mark_room_ready).
        """
        booking = request.env['hotel.booking'].browse(booking_id)
        if not booking.exists():
            return self._prepare_response({'success': False, 'error': 'La reserva solicitada no existe.'}, status=404)

        if booking.status_bar != 'cleaning_needed':
            return self._prepare_response({'success': False, 'error': 'La habitación solo puede marcarse como lista desde el estado "cleaning_needed".'}, status=400)

        try:
            booking.action_mark_room_ready()
            booking.invalidate_recordset(['status_bar'])
        except Exception as e:
            return self._prepare_response({'success': False, 'error': f'Error al marcar la habitación como lista: {e}'}, status=500)

        return self._prepare_response({
            'success': True,
            'message': 'La reserva fue marcada como "Habitación Lista".',
            'data': {
                'reserva_id': booking.id,
                'status_bar': booking.status_bar,
            }
        })
