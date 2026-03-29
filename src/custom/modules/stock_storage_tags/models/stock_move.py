# -*- coding: utf-8 -*-
from odoo import models, fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    storage_tag_ids = fields.Many2many(
        related='product_id.storage_tag_ids',
        string='Etiquetas del Producto',
        readonly=True
    )
