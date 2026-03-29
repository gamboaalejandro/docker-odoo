# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    storage_tag_ids = fields.Many2many(
        'stock.storage.tag',
        'product_template_storage_tag_rel',
        'product_tmpl_id', 'tag_id',
        string='Etiquetas de Almacenamiento'
    )

class ProductProduct(models.Model):
    _inherit = 'product.product'

    storage_tag_ids = fields.Many2many(
        'stock.storage.tag',
        'product_product_storage_tag_rel',
        'product_id', 'tag_id',
        string='Etiquetas de Almacenamiento (Variante)'
    )
