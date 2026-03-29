# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)

class AccountFinancialKpi(models.Model):
    _name = 'account.financial.kpi'
    _description = 'Indicador de Salud Financiera'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre del Indicador', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    formula = fields.Text(string='Fórmula Matemática', required=True, 
                          help="Usa nombres de tipos de cuenta como variables. Ej: asset_current / liability_current")
    evaluation_direction = fields.Selection([
        ('higher_is_better', 'Mayor es mejor (Verde arriba)'),
        ('lower_is_better', 'Menor es mejor (Verde abajo)'),
    ], string='Dirección de Evaluación', default='higher_is_better', required=True)
    
    threshold_warning = fields.Float(string='Umbral de Advertencia (Amarillo)')
    threshold_critical = fields.Float(string='Umbral Crítico (Rojo)')
    
    current_value = fields.Float(string='Valor Actual', compute='_compute_current_value')
    state = fields.Selection([
        ('success', 'Bien'),
        ('warning', 'Aceptable/Advertencia'),
        ('danger', 'Crítico')
    ], string='Estado', compute='_compute_current_value')

    @api.depends('formula', 'threshold_warning', 'threshold_critical', 'evaluation_direction')
    def _compute_current_value(self):
        # 1. Caché de una sola consulta (Batch Processing de Saldos)
        # Esto evitará N+1 queries al evaluar cada fórmula de los N KPIs
        domain = [
            ('parent_state', '=', 'posted'),
            ('company_id', 'in', self.env.companies.ids)
        ]
        
        # Agrupar los saldos (balance) por account_type usando read_group
        # balance = debit - credit
        lines_data = self.env['account.move.line'].read_group(
            domain,
            ['balance:sum'],
            ['account_type']
        )
        
        # Diccionario unificado { 'asset_current': 50000.0, 'liability_current': -20000.0, ... }
        balance_cache = {}
        for res in lines_data:
            acc_type = res.get('account_type')
            if acc_type:
                # Opcional: Invertir saldos de Pasivo y Capital para que den "positivo" en las divisiones financieras,
                # o dejarlos raw (con su signo matemático base Odoo).
                # Usaremos RAW (balance) para que el analista reste o sume de acuerdo al estándar.
                # Nota: Habitualmente Odoo assets > 0, liabilities < 0, income < 0, expense > 0.
                balance_cache[acc_type] = res.get('balance', 0.0)

        # 2. Función Helper Inyectada en safe_eval
        def get_balance(account_type):
            return balance_cache.get(account_type, 0.0)
            
        # Preparar Eval Context con la función helper y también inyectando las llaves como variables directas
        # para que la UX de las fórmulas sea más nativa: `asset_current / liability_current`
        base_eval_context = {'get_balance': get_balance}
        base_eval_context.update(balance_cache)

        # 3. Iterar y calcular
        for kpi in self:
            val = 0.0
            kpi_state = 'success'
            if kpi.formula:
                try:
                    val = float(safe_eval(kpi.formula, base_eval_context))
                except ZeroDivisionError:
                    _logger.warning("División por cero protegida en KPI %s", kpi.name)
                    val = 0.0
                except Exception as e:
                    _logger.error("Error al evaluar el KPI %s: %s", kpi.name, e)
                    val = 0.0
            
            # Evaluación del Semáforo
            if kpi.evaluation_direction == 'higher_is_better':
                if val <= kpi.threshold_critical:
                    kpi_state = 'danger'
                elif val <= kpi.threshold_warning:
                    kpi_state = 'warning'
                else:
                    kpi_state = 'success'
            else: # 'lower_is_better'
                if val >= kpi.threshold_critical:
                    kpi_state = 'danger'
                elif val >= kpi.threshold_warning:
                    kpi_state = 'warning'
                else:
                    kpi_state = 'success'

            kpi.current_value = val
            kpi.state = kpi_state
