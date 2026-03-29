# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type = fields.Selection([
        ('retail', 'Minorista'),
        ('wholesale', 'Mayorista'),
        ('vip', 'VIP')
    ], string='Tipo de Cliente', default='retail', copy=False,
    help="Define el tipo de cliente para las políticas de descuento automático.")
