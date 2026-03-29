# -*- coding: utf-8 -*-
from odoo import models, fields

class StockStorageTag(models.Model):
    _name = 'stock.storage.tag'
    _description = 'Etiqueta de Almacenamiento'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True, translate=True)
    color = fields.Integer(string='Color')
    description = fields.Text(string='Descripción')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'El nombre de la etiqueta debe ser único.')
    ]
