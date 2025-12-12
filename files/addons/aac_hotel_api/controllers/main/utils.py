# -*- coding: utf-8 -*-
import json
import logging
import base64
from datetime import datetime
from functools import wraps
from odoo import http, _
from odoo.http import request, Response
from odoo.tools import json_default
from odoo.exceptions import ValidationError, AccessError, UserError, MissingError
from ..api_auth import validate_api_key

_logger = logging.getLogger(__name__)

# Constantes
MAX_FILE_SIZE_MB = 10
MAX_STAY_DAYS = 365
MIN_AGE = 1
MAX_AGE = 120
ADULT_AGE_THRESHOLD = 18

VALID_STATUSES = [
    "initial",
    "draft",
    "confirmed",
    "checkin",
    "checkout",
    "cleaning_needed",
    "room_ready",
    "cancelled",
    "no_show",
    "allot",
    "check_in",
    "pending",
    "checkout_pending",
]

TERMINAL_STATUSES = ["cancelled", "checkout", "no_show"]

VALID_BOOKING_REFERENCES = ["sale_order", "manual", "agent", "other"]

VALID_GENDERS = ["male", "female", "other"]

VALID_COMMISSION_TYPES = ["fixed", "percentage"]

STATUS_TRANSITIONS = {
    "initial": ["confirmed", "cancelled"],
    "draft": ["confirmed", "cancelled"],
    "confirmed": ["checkin", "check_in", "cancelled", "no_show"],
    "checkin": ["checkout", "cancelled"],
    "check_in": ["checkout", "cancelled"],
    "checkout": ["cleaning_needed"],
    "cleaning_needed": ["room_ready"],
    "room_ready": ["confirmed"],
    "cancelled": ["initial"],
    "no_show": ["initial"],
    "allot": ["checkin", "check_in", "cancelled", "no_show"],
    "pending": ["confirmed", "cancelled"],
}


def handle_api_errors(func):
    """Decorador para manejo centralizado de errores en endpoints"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ValueError as e:
            _logger.warning("Error de validación en %s: %s", func.__name__, str(e))
            return self._prepare_response(
                {"success": False, "error": str(e)}, status=400
            )
        except (AccessError, MissingError) as e:
            _logger.warning("Error de acceso en %s: %s", func.__name__, str(e))
            return self._prepare_response(
                {
                    "success": False,
                    "error": "No tiene permisos para acceder a esta información",
                },
                status=403,
            )
        except UserError as e:
            _logger.warning("Error de usuario en %s: %s", func.__name__, str(e))
            return self._prepare_response(
                {"success": False, "error": str(e)}, status=400
            )
        except Exception as e:
            _logger.exception("Error inesperado en %s: %s", func.__name__, str(e))
            return self._prepare_response(
                {"success": False, "error": "Error interno del servidor"}, status=500
            )

    return wrapper


class HotelApiUtils:

    def _prepare_response(self, data, status=200):
        """Preparar respuesta HTTP con formato JSON + headers CORS"""
        return Response(
            json.dumps(data, default=json_default),
            status=status,
            content_type="application/json",
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
            }
        )

    def _check_access_rights(self, model_name, operation="read", raise_exception=True):
        """Verificar permisos de acceso a un modelo."""
        try:
            if not request.env:
                error_msg = "El entorno de la solicitud no está disponible. Asegúrese de usar el decorador @validate_api_key"
                _logger.error(error_msg)
                if raise_exception:
                    raise AccessError(error_msg)
                return False

            model = request.env[model_name]
            model.check_access_rights(operation, raise_exception=True)
            return True
        except AccessError as e:
            if raise_exception:
                _logger.warning(
                    f"Error de acceso a {model_name} ({operation}): {str(e)}"
                )
                raise
            return False

    def _check_access_rule(self, recordset, operation="read", raise_exception=True):
        """Verificar reglas de acceso para un recordset específico."""
        try:
            if not recordset:
                return True
            recordset.check_access_rule(operation)
            return True
        except AccessError as e:
            if raise_exception:
                _logger.warning(f"Error de regla de acceso ({operation}): {str(e)}")
                raise
            return False

    def _ensure_access(self, recordset, operation="read"):
        """Asegurar que el usuario tiene acceso al recordset."""
        try:
            self._check_access_rights(recordset._name, operation)
            self._check_access_rule(recordset, operation)
            return recordset
        except AccessError:
            if operation == "read" and request.env.user.has_group("base.group_system"):
                _logger.info(
                    f"Usuario {request.env.user.login} usando sudo() para lectura de {recordset._name}"
                )
                return recordset.sudo()
            raise

    def _parse_json_data(self):
        """Parsear datos JSON de la petición"""
        try:
            data = request.httprequest.data
            if not data:
                return {}
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Formato JSON inválido: {str(e)}")

    def _parse_request_data(self):
        """Parsear datos de la petición, soportando tanto JSON como form-data"""
        content_type = request.httprequest.content_type or ""

        has_form = hasattr(request.httprequest, "form") and request.httprequest.form
        has_files = hasattr(request.httprequest, "files") and request.httprequest.files
        is_multipart = (
            "multipart/form-data" in content_type or "form-data" in content_type
        )

        if is_multipart or has_form or has_files:
            data = {}
            try:
                form_dict = (
                    dict(request.httprequest.form)
                    if hasattr(request.httprequest, "form")
                    else {}
                )
                for key, value in form_dict.items():
                    if key == "documents":
                        try:
                            parsed_value = (
                                json.loads(value) if isinstance(value, str) else value
                            )
                            if isinstance(parsed_value, list):
                                data[key] = parsed_value
                            elif isinstance(parsed_value, dict):
                                data[key] = [parsed_value]
                            else:
                                data[key] = parsed_value
                        except json.JSONDecodeError as e:
                            _logger.warning(
                                "Documents no es JSON válido (%s), se ignorará", str(e)
                            )
                    else:
                        data[key] = value
            except Exception as e:
                _logger.error("Error procesando form-data: %s", str(e))

            try:
                files_dict = (
                    dict(request.httprequest.files)
                    if hasattr(request.httprequest, "files")
                    else {}
                )
                if files_dict:
                    documents = data.get("documents", [])
                    if not isinstance(documents, list):
                        documents = []

                    for file_key, file_obj in files_dict.items():
                        if (
                            file_obj
                            and hasattr(file_obj, "filename")
                            and file_obj.filename
                        ):
                            file_obj.seek(0)
                            file_content = file_obj.read()
                            file_base64 = base64.b64encode(file_content).decode("utf-8")

                            doc_found = False
                            for doc in documents:
                                if (
                                    isinstance(doc, dict)
                                    and doc.get("file_name") == file_obj.filename
                                ):
                                    doc["file"] = file_base64
                                    doc_found = True
                                    break

                            if not doc_found:
                                doc_data = {
                                    "name": (
                                        file_obj.filename.rsplit(".", 1)[0]
                                        if "." in file_obj.filename
                                        else file_obj.filename
                                    ),
                                    "file_name": file_obj.filename,
                                    "file": file_base64,
                                }
                                documents.append(doc_data)

                    if documents:
                        data["documents"] = documents
            except Exception as e:
                _logger.error("Error procesando archivos: %s", str(e))

            return data
        else:
            if request.httprequest.data and len(request.httprequest.data) > 0:
                return self._parse_json_data()
            else:
                return {}

    def _parse_datetime(self, date_str, field_name="fecha"):
        """Parsear string a datetime con manejo de errores mejorado"""
        if not date_str:
            raise ValueError(f"{field_name} es requerida")
        try:
            if isinstance(date_str, str):
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(date_str.replace("T", " "), fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Formato de {field_name} no reconocido")
            return date_str
        except Exception as e:
            raise ValueError(f"Error al procesar {field_name}: {str(e)}")

    def _validate_partner_id(self, partner_id_str):
        try:
            partner_id = int(partner_id_str)
            partner = request.env["res.partner"].browse(partner_id)
            if not partner.exists():
                raise ValueError(f"El partner con ID {partner_id} no existe")
            return partner_id
        except (ValueError, TypeError):
            raise ValueError("El partner_id debe ser un número entero válido")

    def _validate_dates(self, check_in_str, check_out_str):
        check_in = self._parse_datetime(check_in_str, "check_in")
        check_out = self._parse_datetime(check_out_str, "check_out")

        if check_out < check_in:
            raise ValueError(
                "La fecha de check-out no puede ser anterior a la fecha de check-in"
            )

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if check_in.date() < today.date():
            raise ValueError("La fecha de check-in no puede ser en el pasado")

        days_diff = (check_out.date() - check_in.date()).days
        if days_diff > MAX_STAY_DAYS:
            raise ValueError(f"La estadía no puede ser mayor a {MAX_STAY_DAYS} días")

        return check_in, check_out

    def _validate_rooms_data(self, rooms_data):
        if not rooms_data or len(rooms_data) == 0:
            raise ValueError("Debe especificar al menos una habitación")

        for i, room in enumerate(rooms_data, start=1):
            product_id = room.get("product_id") or room.get("room_id")
            if not product_id:
                raise ValueError(
                    f"Habitación {i}: Debe especificar el ID del producto (product_id o room_id)"
                )
            try:
                product_id = int(product_id)
            except (ValueError, TypeError):
                raise ValueError(
                    f"Habitación {i}: El product_id debe ser un número válido"
                )

            product = request.env["product.product"].browse(product_id)
            if not product.exists():
                raise ValueError(
                    f"Habitación {i}: El producto con ID {product_id} no existe"
                )
            if not product.is_room_type:
                raise ValueError(
                    f'Habitación {i}: El producto "{product.name}" no es un tipo de habitación'
                )

            if room.get("price") is not None:
                try:
                    price = float(room["price"])
                    if price < 0:
                        raise ValueError(
                            f"Habitación {i}: El precio no puede ser negativo"
                        )
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Habitación {i}: El precio debe ser un número válido"
                    )

            if room.get("discount") is not None:
                try:
                    discount = float(room["discount"])
                    if discount < 0 or discount > 100:
                        raise ValueError(
                            f"Habitación {i}: El descuento debe estar entre 0 y 100"
                        )
                except (ValueError, TypeError):
                    raise ValueError(
                        f"Habitación {i}: El descuento debe ser un número válido"
                    )

            if room.get("guests"):
                self._validate_guests_data(room["guests"], i)

    def _validate_guests_data(self, guests_data, room_number):
        if not guests_data or len(guests_data) == 0:
            raise ValueError(
                f"Habitación {room_number}: Debe especificar al menos un huésped"
            )

        adult_count = 0
        for i, guest in enumerate(guests_data, start=1):
            if not guest.get("name") and not guest.get("partner_id"):
                raise ValueError(
                    f"Habitación {room_number}, Huésped {i}: Debe especificar el nombre o un partner_id"
                )

            if guest.get("partner_id"):
                partner = request.env["res.partner"].browse(guest["partner_id"])
                if not partner.exists():
                    raise ValueError(
                        f'Habitación {room_number}, Huésped {i}: El partner con ID {guest["partner_id"]} no existe'
                    )

            if not guest.get("age"):
                raise ValueError(
                    f"Habitación {room_number}, Huésped {i}: Debe especificar la edad"
                )

            try:
                age = int(guest["age"])
                if age < MIN_AGE:
                    raise ValueError(
                        f"Habitación {room_number}, Huésped {i}: La edad debe ser mayor a {MIN_AGE - 1}"
                    )
                if age > MAX_AGE:
                    raise ValueError(
                        f"Habitación {room_number}, Huésped {i}: La edad no puede ser mayor a {MAX_AGE} años"
                    )
            except (ValueError, TypeError):
                raise ValueError(
                    f"Habitación {room_number}, Huésped {i}: La edad debe ser un número válido"
                )

            if age >= ADULT_AGE_THRESHOLD:
                adult_count += 1

            if guest.get("gender") and guest["gender"] not in VALID_GENDERS:
                raise ValueError(
                    f'Habitación {room_number}, Huésped {i}: Género inválido. Debe ser: {", ".join(VALID_GENDERS)}'
                )

        if adult_count == 0:
            raise ValueError(
                f"Habitación {room_number}: Debe haber al menos un adulto por habitación"
            )

    def _validate_booking_status(self, status):
        if status and status not in VALID_STATUSES:
            raise ValueError(
                f'Estado inválido: {status}. Estados válidos: {", ".join(VALID_STATUSES)}'
            )

    def _validate_documents_data(self, documents_data):
        if not documents_data:
            return
        for i, doc in enumerate(documents_data, start=1):
            if not doc.get("name"):
                raise ValueError(
                    f"Documento {i}: Debe especificar el nombre del documento"
                )
            if doc.get("file"):
                try:
                    file_data = base64.b64decode(doc["file"])
                    file_size_mb = len(file_data) / (1024 * 1024)
                    if file_size_mb > MAX_FILE_SIZE_MB:
                        raise ValueError(
                            f"Documento {i}: El archivo no puede ser mayor a {MAX_FILE_SIZE_MB}MB"
                        )
                except Exception:
                    raise ValueError(
                        f"Documento {i}: Formato de archivo inválido (debe ser base64)"
                    )

    def _validate_hotel_id(self, hotel_id):
        if not hotel_id:
            raise ValueError("El hotel_id es requerido")
        try:
            hotel_id = int(hotel_id)
            hotel = request.env["hotel.hotels"].browse(hotel_id)
            if not hotel.exists():
                raise ValueError(f"El hotel con ID {hotel_id} no existe")
            return hotel_id
        except (ValueError, TypeError) as e:
            if isinstance(e, ValueError) and "hotel_id" in str(e).lower():
                raise
            raise ValueError("El hotel_id debe ser un número entero válido")

    def _validate_booking_reference(self, booking_reference):
        if booking_reference and booking_reference not in VALID_BOOKING_REFERENCES:
            raise ValueError(
                f'Referencia de reserva inválida: {booking_reference}. Referencias válidas: {", ".join(VALID_BOOKING_REFERENCES)}'
            )

    def _validate_agent_data(self, data):
        if not data.get("via_agent"):
            return
        if not data.get("agent_id"):
            raise ValueError("Debe especificar el agente cuando via_agent es True")
        agent = request.env["res.partner"].browse(data["agent_id"])
        if not agent.exists():
            raise ValueError(f'El agente con ID {data["agent_id"]} no existe')

        commission_type = data.get("commission_type")
        if commission_type:
            if commission_type not in VALID_COMMISSION_TYPES:
                raise ValueError(
                    f'Tipo de comisión debe ser: {", ".join(VALID_COMMISSION_TYPES)}'
                )

            if commission_type == "fixed":
                if not data.get("agent_commission_amount"):
                    raise ValueError("Debe especificar el monto de comisión fija")
                try:
                    amount = float(data["agent_commission_amount"])
                    if amount < 0:
                        raise ValueError("El monto de comisión no puede ser negativo")
                except (ValueError, TypeError):
                    raise ValueError("El monto de comisión debe ser un número válido")

            if commission_type == "percentage":
                if not data.get("agent_commission_percentage"):
                    raise ValueError("Debe especificar el porcentaje de comisión")
                try:
                    percentage = float(data["agent_commission_percentage"])
                    if percentage < 0 or percentage > 100:
                        raise ValueError(
                            "El porcentaje de comisión debe estar entre 0 y 100"
                        )
                except (ValueError, TypeError):
                    raise ValueError(
                        "El porcentaje de comisión debe ser un número válido"
                    )

    def _validate_booking_for_update(self, booking, data):
        if booking.status_bar in TERMINAL_STATUSES:
            raise ValueError(
                f'No se puede actualizar una reserva en estado "{booking.status_bar}"'
            )
        if "status_bar" in data:
            self._validate_status_transition(booking.status_bar, data["status_bar"])

    def _validate_status_transition(self, current_status, new_status):
        allowed_transitions = STATUS_TRANSITIONS.get(current_status, [])
        normalized_allowed = set(allowed_transitions)
        if "checkin" in normalized_allowed:
            normalized_allowed.add("check_in")
        if "check_in" in normalized_allowed:
            normalized_allowed.add("checkin")

        if new_status not in normalized_allowed:
            raise ValueError(
                f'No se puede cambiar de estado "{current_status}" a "{new_status}". Transiciones válidas: {", ".join(sorted(allowed_transitions)) if allowed_transitions else "ninguna"}'
            )

    def _validate_required_fields(self, data, required_fields):
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            raise ValueError(
                f'Campos requeridos faltantes: {", ".join(missing_fields)}'
            )
