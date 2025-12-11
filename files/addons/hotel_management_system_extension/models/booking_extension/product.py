# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductTemplateExtension(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir create para marcar automáticamente habitaciones nuevas como listas
        """
        # Crear el producto template primero
        products = super().create(vals_list)

        # Para cada producto template creado, verificar si es una habitación
        for product in products:
            if hasattr(product, "is_room_type") and product.is_room_type:
                # Marcar la habitación como lista automáticamente
                product._mark_new_room_template_as_ready()

        return products

    def _mark_new_room_template_as_ready(self):
        """
        Marcar una habitación nueva como lista (ROOM_READY)
        """
        self.ensure_one()

        # Solo procesar si es una habitación
        if not hasattr(self, "is_room_type") or not self.is_room_type:
            return

        # Crear un mensaje de seguimiento
        self.message_post(
            body=_(
                "Habitación nueva creada automáticamente marcada como lista (ROOM_READY). Disponible para reservas inmediatamente."
            ),
            subject=_("Habitación Nueva - Lista"),
        )

        # Log para debugging
        _logger.info(
            "Habitación nueva (template) %s (ID: %s) marcada automáticamente como ROOM_READY",
            self.name,
            self.id,
        )

        return True


class ProductExtension(models.Model):
    _inherit = "product.product"

    # Campo para el estado de la habitación
    room_status = fields.Selection(
        [
            ("available", "Disponible"),
            ("occupied", "Ocupada"),
            ("cleaning", "En Limpieza"),
            ("maintenance", "En Mantenimiento"),
            ("blocked", "Bloqueada"),
        ],
        string="Estado de Habitación",
        default="available",
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribir create para marcar automáticamente habitaciones nuevas como listas
        """
        # Crear el producto primero
        products = super().create(vals_list)

        # Para cada producto creado, verificar si es una habitación
        for product in products:
            if hasattr(product, "is_room_type") and product.is_room_type:
                # Marcar la habitación como lista automáticamente
                product._mark_new_room_as_ready()

        return products

    def _mark_new_room_as_ready(self):
        """
        Marcar una habitación nueva como lista (ROOM_READY)
        """
        self.ensure_one()

        # Solo procesar si es una habitación
        if not hasattr(self, "is_room_type") or not self.is_room_type:
            return

        # Marcar como disponible automáticamente
        self.room_status = "available"

        # Crear un mensaje de seguimiento
        self.message_post(
            body=_(
                "Habitación nueva creada automáticamente marcada como lista (ROOM_READY). Disponible para reservas inmediatamente."
            ),
            subject=_("Habitación Nueva - Lista"),
        )

        # Log para debugging
        _logger.info(
            "Habitación nueva %s (ID: %s) marcada automáticamente como ROOM_READY",
            self.name,
            self.id,
        )

        return True
