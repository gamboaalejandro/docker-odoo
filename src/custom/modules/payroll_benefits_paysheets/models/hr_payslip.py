import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

# Frequency-to-month mapping for LOTTT benefit rules
# Quarterly: months 3, 6, 9, 12
# Yearly: month 12 only
_FREQUENCY_MONTHS = {
    'quarterly': {3, 6, 9, 12},
    'yearly': {12},
}


class HrPayslipBenefitLine(models.Model):
    _name = 'hr.payslip.benefit.line'
    _description = 'Línea de Beneficio en Nómina'

    payslip_id = fields.Many2one(
        'hr.payroll.test',
        string='Nómina',
        required=True,
        ondelete='cascade',
    )
    rule_id = fields.Many2one(
        'hr.benefit.rule',
        string='Regla de Beneficio',
        required=True,
        ondelete='restrict',
    )
    benefit_type = fields.Selection(
        related='rule_id.benefit_type',
        string='Tipo de Beneficio',
        store=True,
        readonly=True,
    )
    amount = fields.Float(
        string='Monto Calculado',
        digits=(16, 2),
    )
    note = fields.Char(
        string='Detalle',
    )


class HrPayrollTest(models.Model):
    _name = 'hr.payroll.test'
    _description = 'Simulación de Nómina para Pruebas (LOTTT)'

    name = fields.Char(string='Referencia', required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True, ondelete='cascade')
    contract_id = fields.Many2one('hr.contract', string='Contrato', required=True, ondelete='cascade')
    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    benefit_line_ids = fields.One2many(
        'hr.payslip.benefit.line',
        'payslip_id',
        string='Beneficios LOTTT',
        readonly=True,
    )

    total_benefits = fields.Float(
        string='Total Beneficios',
        compute='_compute_total_benefits',
        store=True,
    )

    @api.depends('benefit_line_ids.amount')
    def _compute_total_benefits(self):
        for payslip in self:
            payslip.total_benefits = sum(
                payslip.benefit_line_ids.mapped('amount')
            )

    def action_compute_sheet(self):
        """Action button to simulate computing the sheet."""
        for payslip in self:
            payslip._compute_benefit_lines()

    def _compute_benefit_lines(self):
        """Calculate and attach benefit lines based on matching rules."""
        self.ensure_one()
        BenefitLine = self.env['hr.payslip.benefit.line']
        Rule = self.env['hr.benefit.rule']

        # Remove existing benefit lines for recomputation
        self.benefit_line_ids.unlink()

        contract = self.contract_id
        if not contract:
            return

        # Fallback: if contract_type_ve is empty/None, default to full_time
        contract_type = contract.contract_type_ve or 'full_time'

        # Find matching rules for this contract type
        rules = Rule.search([
            ('contract_type', '=', contract_type),
            ('active', '=', True),
        ])

        if not rules:
            _logger.info(
                "No benefit rules found for contract type '%s' on payslip %s",
                contract_type, self.name or self.id,
            )
            return

        # Build evaluation context
        eval_context = self._get_benefit_eval_context(contract)

        # Determine payslip month for frequency filtering
        payslip_month = self.date_to.month if self.date_to else 12

        # Get currency for precision rounding
        currency = self.company_id.currency_id or self.env.company.currency_id

        # Accumulate benefit line vals for batch creation
        line_vals_list = []

        for rule in rules:
            # --- Frequency filtering ---
            if not self._should_apply_rule_for_frequency(rule.frequency, payslip_month):
                _logger.debug(
                    "Skipping rule '%s' (freq=%s): not applicable in month %d",
                    rule.name, rule.frequency, payslip_month,
                )
                continue

            # --- Minimum service months check ---
            service_months = eval_context.get('service_months', 0)
            if rule.min_service_months > 0 and service_months < rule.min_service_months:
                _logger.info(
                    "Skipping rule '%s': employee has %d months, requires %d",
                    rule.name, service_months, rule.min_service_months,
                )
                continue

            # --- Evaluate formula using safe_eval ---
            try:
                amount = self._evaluate_benefit_formula(
                    rule.formula, eval_context
                )
            except Exception as e:
                raise UserError(
                    "Error al calcular la regla '%(rule)s' "
                    "(código: %(code)s): %(error)s" % {
                        'rule': rule.name,
                        'code': rule.code,
                        'error': str(e),
                    }
                )

            if amount is None or amount < 0:
                amount = 0.0

            # Round using company currency precision
            if currency:
                amount = currency.round(amount)

            line_vals_list.append({
                'payslip_id': self.id,
                'rule_id': rule.id,
                'amount': amount,
                'note': '%s (%s)' % (rule.name, rule.frequency),
            })

        # Batch creation: single create() call for all lines
        if line_vals_list:
            BenefitLine.create(line_vals_list)

    @staticmethod
    def _should_apply_rule_for_frequency(frequency, payslip_month):
        """Determine whether a rule should be applied based on its frequency
        and the payslip month.
        """
        if frequency in ('monthly', 'end_of_contract'):
            return True
        allowed_months = _FREQUENCY_MONTHS.get(frequency)
        if allowed_months is None:
            return True
        return payslip_month in allowed_months

    def _get_benefit_eval_context(self, contract):
        """Build the variable context for formula evaluation."""
        salary_base = contract.wage or 0.0
        vac_days = contract.vacation_bonus_days or 15
        util_days = contract.utilities_days or 30
        cesta_ticket = contract.cesta_ticket_amount or 0.0

        vacation_bonus_aliquot = salary_base * vac_days / 360
        utilities_aliquot = salary_base * util_days / 360
        integral_salary = salary_base + vacation_bonus_aliquot + utilities_aliquot
        integral_daily_salary = integral_salary / 30 if integral_salary else 0.0

        service_years = contract.service_years or 0
        service_months = contract.service_months or 0
        work_factor = contract.work_factor or 1.0

        return {
            'salary_base': salary_base,
            'vacation_bonus_days': vac_days,
            'utilities_days': util_days,
            'vacation_bonus_aliquot': vacation_bonus_aliquot,
            'utilities_aliquot': utilities_aliquot,
            'integral_salary': integral_salary,
            'integral_daily_salary': integral_daily_salary,
            'service_years': service_years,
            'service_months': service_months,
            'cesta_ticket_amount': cesta_ticket,
            'work_factor': work_factor,
        }

    def _evaluate_benefit_formula(self, formula, context):
        """Evaluate a benefit formula string using Odoo's safe_eval."""
        eval_locals = dict(context)
        eval_locals.update({
            'round': round,
            'min': min,
            'max': max,
            'abs': abs,
        })
        try:
            result = safe_eval(formula.strip(), eval_locals)
            return float(result)
        except Exception as e:
            _logger.error(
                "Formula evaluation error: %s | formula: %s", e, formula
            )
            raise
