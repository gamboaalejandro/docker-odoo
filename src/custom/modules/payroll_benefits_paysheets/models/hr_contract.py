from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'

    contract_type_ve = fields.Selection(
        selection=[
            ('full_time', 'Tiempo Completo'),
            ('part_time', 'Medio Tiempo'),
            ('temporary', 'Temporal'),
        ],
        string='Tipo de Contrato (LOTTT)',
        default='full_time',
        required=True,
        tracking=True,
        help='Tipo de contrato según la legislación venezolana (LOTTT).',
    )

    cesta_ticket_amount = fields.Float(
        string='Cesta Ticket (Mensual)',
        default=0.0,
        tracking=True,
        help='Monto mensual del beneficio de alimentación (Cesta Ticket).',
    )

    vacation_bonus_days = fields.Integer(
        string='Días Bono Vacacional',
        default=15,
        tracking=True,
        help='Días de bono vacacional. Mínimo legal LOTTT: 15 días. '
             'Se incrementa 1 día por año de servicio.',
    )

    utilities_days = fields.Integer(
        string='Días de Utilidades',
        default=30,
        tracking=True,
        help='Días de utilidades. Rango legal LOTTT: entre 30 y 120 días.',
    )

    integral_salary = fields.Float(
        string='Salario Integral',
        compute='_compute_integral_salary',
        store=True,
        help='Salario Base + Alícuota de Bono Vacacional + Alícuota de Utilidades.',
    )

    integral_daily_salary = fields.Float(
        string='Salario Integral Diario',
        compute='_compute_integral_salary',
        store=True,
        help='Salario Integral / 30.',
    )

    service_years = fields.Integer(
        string='Años de Servicio',
        compute='_compute_service_time',
        help='Años de antigüedad del empleado en la empresa.',
    )

    service_months = fields.Integer(
        string='Meses de Servicio',
        compute='_compute_service_time',
        help='Total de meses de antigüedad del empleado.',
    )

    work_factor = fields.Float(
        string='Factor de Jornada',
        compute='_compute_work_factor',
        store=True,
        help='Factor aplicable según tipo de contrato: '
             'TC=1.0, MT=0.5, Temp=1.0',
    )

    @api.depends('wage', 'vacation_bonus_days', 'utilities_days')
    def _compute_integral_salary(self):
        for contract in self:
            salary_base = contract.wage or 0.0
            vac_days = contract.vacation_bonus_days or 0
            util_days = contract.utilities_days or 0

            vacation_bonus_aliquot = salary_base * vac_days / 360
            utilities_aliquot = salary_base * util_days / 360

            contract.integral_salary = (
                salary_base + vacation_bonus_aliquot + utilities_aliquot
            )
            contract.integral_daily_salary = (
                contract.integral_salary / 30 if contract.integral_salary else 0.0
            )

    @api.depends('date_start')
    def _compute_service_time(self):
        today = fields.Date.today()
        for contract in self:
            if contract.date_start:
                delta = relativedelta(today, contract.date_start)
                contract.service_years = delta.years
                contract.service_months = delta.years * 12 + delta.months
            else:
                contract.service_years = 0
                contract.service_months = 0

    @api.depends('contract_type_ve')
    def _compute_work_factor(self):
        factors = {
            'full_time': 1.0,
            'part_time': 0.5,
            'temporary': 1.0,
        }
        for contract in self:
            contract.work_factor = factors.get(
                contract.contract_type_ve, 1.0
            )

    @api.constrains('utilities_days')
    def _check_utilities_days(self):
        for contract in self:
            if contract.utilities_days < 30 or contract.utilities_days > 120:
                raise ValidationError(
                    'Los días de utilidades deben estar entre 30 y 120 '
                    'según la LOTTT (Art. 131-132).'
                )

    @api.constrains('vacation_bonus_days')
    def _check_vacation_bonus_days(self):
        for contract in self:
            if contract.vacation_bonus_days < 15:
                raise ValidationError(
                    'Los días de bono vacacional no pueden ser menores a 15 '
                    'según la LOTTT (Art. 192).'
                )

    @api.constrains('cesta_ticket_amount')
    def _check_cesta_ticket_amount(self):
        for contract in self:
            if contract.cesta_ticket_amount < 0:
                raise ValidationError(
                    'El monto de Cesta Ticket no puede ser negativo.'
                )

    @api.constrains('wage')
    def _check_wage_positive(self):
        for contract in self:
            if contract.wage is not None and contract.wage < 0:
                raise ValidationError(
                    'El salario base no puede ser negativo.'
                )
