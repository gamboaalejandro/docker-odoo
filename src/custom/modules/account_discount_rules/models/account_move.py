# -*- coding: utf-8 -*-
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        Sobrescribe action_post para aplicar reglas de descuento automáticas
        justo antes de validar la factura y asentar.
        """
        _logger.warning(">>> ACTION_POST called on %s", self.ids)
        self._apply_automatic_customer_discounts()
        return super(AccountMove, self).action_post()

    def _apply_automatic_customer_discounts(self):
        """
        Aplica las reglas de descuento en lotes. Evalúa reglas por tipo de cliente,
        cliente específico o producto. Ignora líneas que ya tienen un descuento manual
        aplicado para proteger la intencionalidad del contador.
        """
        # Solo procesamos facturas de cliente en estado borrador
        out_invoices = self.filtered(lambda m: m.is_sale_document() and m.state == 'draft')
        _logger.warning(">>> out_invoices: %s", out_invoices.ids)
        if not out_invoices:
            return

        all_rules = self.env['account.discount.rule'].search([])

        for move in out_invoices:
            partner = move.partner_id
            if not partner:
                continue
                
            customer_type = partner.customer_type or 'retail'

            for line in move.invoice_line_ids:
                # Si la línea ya tiene un descuento manual o no tiene producto
                if line.discount > 0.0 or not line.product_id or (line.display_type and line.display_type != 'product'):
                    _logger.warning(">>> Skipping line %s discount=%s product=%s display=%s", line.id, line.discount, line.product_id.id, line.display_type)
                    continue

                product = line.product_id
                _logger.warning(">>> Processing line %s with product %s", line.id, product.id)


                # Filtramos las reglas en memoria para la línea específica
                for rule in all_rules:
                    # 1. Partner específico
                    if rule.partner_id and rule.partner_id != partner:
                        continue
                    # 2. Customer type (sólo si no es partner específico)
                    if not rule.partner_id and rule.customer_type and rule.customer_type != customer_type:
                        continue
                    # 3. Producto específico
                    if rule.product_id and rule.product_id != product:
                        continue

                    # Match encontrado (por orden de secuencia)
                    calculated_discount = rule._compute_discount(line)
                    
                    if calculated_discount > 0.0:
                        line.write({'discount': calculated_discount})
                        break # Solo aplicamos la regla más prioritaria por línea
        
        # Sincronizamos las líneas impositivas y de cobro después de la actualización masiva
        # de descuentos para asegurar la cuadratura del asiento contable.
        for move in out_invoices:
            if hasattr(move, '_sync_dynamic_lines'):
                move._sync_dynamic_lines({'check_move_validity': False})
        
        pass
