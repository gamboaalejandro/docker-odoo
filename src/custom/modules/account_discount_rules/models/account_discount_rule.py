# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

class AccountDiscountRule(models.Model):
    _name = 'account.discount.rule'
    _description = 'Regla de Descuento de Facturación'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Nombre de la Regla', required=True, translate=True)
    sequence = fields.Integer(string='Secuencia', default=10, 
        help="Las reglas con menor secuencia tienen mayor prioridad al momento de ser evaluadas.")
    active = fields.Boolean(string='Activo', default=True)

    # Condiciones (Match)
    customer_type = fields.Selection([
        ('retail', 'Minorista'),
        ('wholesale', 'Mayorista'),
        ('vip', 'VIP')
    ], string='Tipo de Cliente (General)',
        help="Si se establece, esta regla aplicará a todos los clientes de este tipo.")
    
    partner_id = fields.Many2one('res.partner', string='Cliente Específico', 
        help="Si se establece, esta regla aplicará únicamente a este cliente, ignorando el Tipo de Cliente.")
    
    product_id = fields.Many2one('product.product', string='Producto Específico',
        help="Si se establece, el descuento sólo se aplicará a las líneas que contengan este producto.")

    # Acciones (Descuento)
    discount_type = fields.Selection([
        ('percentage', 'Porcentaje Fijo'),
        ('formula', 'Fórmula Dinámica')
    ], string='Tipo de Descuento', required=True, default='percentage')
    
    discount_percentage = fields.Float(string='Descuento (%)', default=0.0)
    
    discount_formula = fields.Text(string='Fórmula de Descuento',
        help="Escribe código Python que asigne un valor flotante a la variable 'result'.\n"
             "Variables disponibles:\n"
             "- line: account.move.line actual\n"
             "- partner: res.partner de la factura\n"
             "- product: product.product de la línea\n"
             "Ejemplo: result = 15.0 si line.quantity > 10 else 5.0")

    @api.constrains('discount_type', 'discount_formula')
    def _check_formula_syntax(self):
        """Valida que la fórmula contenga sintaxis Python válida y asigne a 'result'."""
        for rule in self:
            if rule.discount_type == 'formula':
                if not rule.discount_formula:
                    raise ValidationError("Debe proporcionar una fórmula si seleccionó 'Fórmula Dinámica'.")
                if 'result = ' not in rule.discount_formula and 'result=' not in rule.discount_formula:
                    raise ValidationError("La fórmula debe asignar un valor de descuento en porcentaje a la variable 'result'. Ejemplo: result = 10.0")
                try:
                    # Probamos compilar el código para detectar errores de sintaxis
                    compile(rule.discount_formula, '<string>', 'exec')
                except Exception as e:
                    raise ValidationError(f"Error de sintaxis en la fórmula de la regla '{rule.name}':\n{str(e)}")

    def _compute_discount(self, line):
        """
        Evalúa la regla y retorna el porcentaje de descuento a aplicar sobre la línea de factura dada.
        Retorna 0.0 si la fórmula falla.
        """
        self.ensure_one()
        if self.discount_type == 'percentage':
            return self.discount_percentage
        
        # Evaluar fórmula dinámica
        try:
            localdict = {
                'line': line,
                'partner': line.move_id.partner_id,
                'product': line.product_id,
                'result': 0.0,
            }
            # Limitamos el entorno de ejecución por seguridad
            safe_eval(self.discount_formula, localdict, mode='exec', nocopy=True)
            return float(localdict.get('result', 0.0))
        except Exception:
            # En caso de error de evaluación, retornamos 0 para no bloquear el post de la factura
            # Idealmente se guardaría un log de error aquí
            return 0.0
