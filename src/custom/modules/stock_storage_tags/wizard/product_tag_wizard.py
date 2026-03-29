# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTagWizard(models.TransientModel):
    _name = 'product.tag.wizard'
    _description = 'Asistente Rápido de Etiquetas'

    product_tmpl_id = fields.Many2one('product.template', string='Producto (Plantilla)')
    product_id = fields.Many2one('product.product', string='Producto (Variante)')
    
    storage_tag_ids = fields.Many2many(
        'stock.storage.tag',
        string='Etiquetas Asignadas'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(ProductTagWizard, self).default_get(fields_list)
        # Cargamos las etiquetas pre-configuradas dependiendo del contexto en el que estamos (Plantilla vs Variante)
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model')

        if active_model == 'product.template' and active_id:
            product_tmpl = self.env['product.template'].browse(active_id)
            res.update({
                'product_tmpl_id': product_tmpl.id,
                'storage_tag_ids': [(6, 0, product_tmpl.storage_tag_ids.ids)]
            })
        elif active_model == 'product.product' and active_id:
            product = self.env['product.product'].browse(active_id)
            res.update({
                'product_id': product.id,
                'storage_tag_ids': [(6, 0, product.storage_tag_ids.ids)]
            })
        return res

    def action_apply_tags(self):
        self.ensure_one()
        # Se actualizan las etiquetas dependiendo del modelo sobre el cual se presionó el botón
        if self.product_tmpl_id:
            self.product_tmpl_id.write({'storage_tag_ids': [(6, 0, self.storage_tag_ids.ids)]})
        elif self.product_id:
            self.product_id.write({'storage_tag_ids': [(6, 0, self.storage_tag_ids.ids)]})
            
        return {'type': 'ir.actions.act_window_close'}
