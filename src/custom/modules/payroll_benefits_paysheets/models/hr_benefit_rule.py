from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrBenefitRule(models.Model):
    _name = 'hr.benefit.rule'
    _description = 'Regla de Beneficio Laboral (LOTTT)'
    _order = 'contract_type, benefit_type'

    name = fields.Char(
        string='Nombre de la Regla',
        required=True,
    )
    code = fields.Char(
        string='Código Técnico',
        required=True,
        help='Código único para identificar la regla (ej: UTIL_FT)',
    )
    contract_type = fields.Selection(
        selection=[
            ('full_time', 'Tiempo Completo'),
            ('part_time', 'Medio Tiempo'),
            ('temporary', 'Temporal'),
        ],
        string='Tipo de Contrato',
        required=True,
    )
    benefit_type = fields.Selection(
        selection=[
            ('utilities', 'Utilidades'),
            ('vacation_bonus', 'Bono Vacacional'),
            ('social_benefits_guarantee', 'Prestaciones Sociales (Garantía)'),
            ('cesta_ticket', 'Cesta Ticket'),
        ],
        string='Tipo de Beneficio',
        required=True,
    )
    formula = fields.Text(
        string='Fórmula de Cálculo',
        required=True,
        help="""Expresión Python evaluada en contexto con las siguientes variables:
        - salary_base: Salario base mensual (contract.wage)
        - vacation_bonus_days: Días de bono vacacional configurados
        - utilities_days: Días de utilidades configurados (30-120)
        - vacation_bonus_aliquot: salary_base * vacation_bonus_days / 360
        - utilities_aliquot: salary_base * utilities_days / 360
        - integral_salary: salary_base + vacation_bonus_aliquot + utilities_aliquot
        - integral_daily_salary: integral_salary / 30
        - service_years: Años de servicio del empleado
        - service_months: Meses de servicio del empleado
        - cesta_ticket_amount: Monto fijo de cesta ticket del contrato
        - work_factor: 1.0 (TC), 0.5 (MT), 1.0 (Temp)
        """,
    )
    frequency = fields.Selection(
        selection=[
            ('monthly', 'Mensual'),
            ('quarterly', 'Trimestral'),
            ('yearly', 'Anual'),
            ('end_of_contract', 'Fin de Contrato'),
        ],
        string='Frecuencia de Aplicación',
        required=True,
    )
    min_service_months = fields.Integer(
        string='Meses Mínimos de Servicio',
        default=0,
        help='Meses mínimos de antigüedad para aplicar esta regla. 0 = sin mínimo.',
    )
    active = fields.Boolean(
        string='Activa',
        default=True,
    )
    description = fields.Text(
        string='Descripción / Base Legal',
        help='Referencia a la base legal LOTTT aplicable.',
    )

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)',
         'El código de la regla debe ser único.'),
        ('check_min_service_months', 'CHECK(min_service_months >= 0)',
         'Los meses mínimos de servicio no pueden ser negativos.'),
    ]

    @api.constrains('formula')
    def _check_formula_syntax(self):
        """Validate that the formula has valid Python syntax."""
        for rule in self:
            if rule.formula:
                try:
                    compile(rule.formula.strip(), '<benefit_rule>', 'eval')
                except SyntaxError as e:
                    raise ValidationError(
                        f"Error de sintaxis en la fórmula de la regla "
                        f"'{rule.name}': {e}"
                    )
