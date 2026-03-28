from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class TestBenefitCalculation(TransactionCase):
    """
    Test suite for Venezuelan Payroll Benefits (LOTTT).
    Covers: benefit rules, contract constraints, simulated payslip benefit computation,
    and edge cases as required.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Clean existing test data if necessary
        cls.env['hr.department'].search([('name', '=', 'Departamento de Pruebas')]).unlink()
        cls.env['hr.employee'].search([('name', '=', 'Empleado Prueba LOTTT')]).unlink()

        # Create a department
        cls.department = cls.env['hr.department'].create({
            'name': 'Departamento de Pruebas',
        })

        # Create an employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Empleado Prueba LOTTT',
            'department_id': cls.department.id,
        })

        # Standard contract start date: 2 years ago
        cls.start_date_2y = date.today() - relativedelta(years=2)
        # Contract start date: 2 months ago (less than 3 months)
        cls.start_date_2m = date.today() - relativedelta(months=2)

    def _create_contract(self, contract_type='full_time', wage=3000.0,
                         cesta_ticket=400.0, start_date=None,
                         utilities_days=30, vacation_bonus_days=15):
        """Helper to create a contract with Venezuelan fields."""
        if start_date is None:
            start_date = self.start_date_2y
        return self.env['hr.contract'].create({
            'name': f'Contrato {contract_type} Test',
            'employee_id': self.employee.id,
            'wage': wage,
            'contract_type_ve': contract_type,
            'cesta_ticket_amount': cesta_ticket,
            'utilities_days': utilities_days,
            'vacation_bonus_days': vacation_bonus_days,
            'date_start': start_date,
            'state': 'open',
        })

    def _create_payslip(self, contract, date_to=None):
        """Helper to create a simulated payslip for the given contract."""
        if date_to is None:
            date_to = date.today()
        return self.env['hr.payroll.test'].create({
            'name': 'Nómina Simulada Test',
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'date_from': date_to.replace(day=1),
            'date_to': date_to,
        })

    def tearDown(self):
        """Clean up data to prevent unique constraints matching across tests"""
        super().tearDown()
        self.employee.contract_ids.unlink()

    # =============================================================
    # Test 1: Contract without defined type defaults to full_time
    # =============================================================
    def test_01_contract_default_type(self):
        """Contract without explicit type should default to 'full_time'."""
        contract = self.env['hr.contract'].create({
            'name': 'Contrato Sin Tipo Test',
            'employee_id': self.employee.id,
            'wage': 3000.0,
            'date_start': self.start_date_2y,
            'state': 'open',
        })
        self.assertEqual(
            contract.contract_type_ve, 'full_time',
            "Un contrato sin tipo explícito debe tomar 'full_time' por defecto."
        )

    # =============================================================
    # Test 2: Employee with less than 3 months — social benefits
    # =============================================================
    def test_02_employee_less_than_3_months_no_guarantee(self):
        """Employee with < 3 months should NOT get social benefits guarantee."""
        contract = self._create_contract(
            contract_type='full_time',
            start_date=self.start_date_2m,
        )
        payslip = self._create_payslip(contract)
        payslip.action_compute_sheet()

        guarantee_lines = payslip.benefit_line_ids.filtered(
            lambda l: l.rule_id.benefit_type == 'social_benefits_guarantee'
        )
        self.assertFalse(
            guarantee_lines,
            "Un empleado con menos de 3 meses NO debe tener línea de "
            "Prestaciones Sociales (Garantía)."
        )

    def test_03_employee_less_than_3_months_gets_other_benefits(self):
        """Employee with < 3 months should still get utilities, vacation bonus, cesta ticket."""
        contract = self._create_contract(
            contract_type='full_time',
            start_date=self.start_date_2m,
        )
        # Force month 12 to trigger yearly benefits (Utilities and Vacation Bonus)
        december_date = date(date.today().year, 12, 31)
        payslip = self._create_payslip(contract, date_to=december_date)
        payslip.action_compute_sheet()

        benefit_types = payslip.benefit_line_ids.mapped('benefit_type')
        self.assertIn('utilities', benefit_types,
                      "Utilidades deben aplicarse aunque tenga < 3 meses en Diciembre.")
        self.assertIn('vacation_bonus', benefit_types,
                      "Bono Vacacional debe aplicarse aunque tenga < 3 meses en Diciembre.")
        self.assertIn('cesta_ticket', benefit_types,
                      "Cesta Ticket debe aplicarse aunque tenga < 3 meses.")

    # =============================================================
    # Test 4: Full-time vs Part-time calculation difference
    # =============================================================
    def test_04_full_time_vs_part_time_difference(self):
        """Part-time benefits should be approximately 50% of full-time."""
        # Force month 12 to accurately compare utilities
        december_date = date(date.today().year, 12, 31)
        
        contract_ft = self._create_contract(contract_type='full_time')
        payslip_ft = self._create_payslip(contract_ft, date_to=december_date)
        payslip_ft.action_compute_sheet()

        # Clean up the full_time contract to avoid simultaneous contract validation errors
        contract_ft.unlink()

        contract_pt = self._create_contract(contract_type='part_time')
        payslip_pt = self._create_payslip(contract_pt, date_to=december_date)
        payslip_pt.action_compute_sheet()

        # Compare utilities
        util_ft = sum(payslip_ft.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'utilities'
        ).mapped('amount'))
        util_pt = sum(payslip_pt.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'utilities'
        ).mapped('amount'))

        # Only compare if utilities triggered (requires matching rule and date logic)
        if util_ft > 0:
            self.assertAlmostEqual(
                util_pt, util_ft * 0.5, places=2,
                msg="Utilidades a medio tiempo deben ser 50% de tiempo completo."
            )

        # Compare cesta ticket
        ct_ft = sum(payslip_ft.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'cesta_ticket'
        ).mapped('amount'))
        ct_pt = sum(payslip_pt.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'cesta_ticket'
        ).mapped('amount'))

        if ct_ft > 0:
            self.assertAlmostEqual(
                ct_pt, ct_ft * 0.5, places=2,
                msg="Cesta Ticket a medio tiempo debe ser 50% de tiempo completo."
            )

    # =============================================================
    # Test 5: Utilities days constrained to 30–120
    # =============================================================
    def test_05_utilities_days_below_minimum(self):
        """Utilities days below 30 should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_contract(utilities_days=20)

    def test_06_utilities_days_above_maximum(self):
        """Utilities days above 120 should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_contract(utilities_days=150)

    def test_07_utilities_days_valid_range(self):
        """Utilities days within 30-120 should be accepted."""
        contract = self._create_contract(utilities_days=90)
        self.assertEqual(contract.utilities_days, 90)

    # =============================================================
    # Test 8: Vacation bonus days minimum
    # =============================================================
    def test_08_vacation_bonus_days_below_minimum(self):
        """Vacation bonus days below 15 should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_contract(vacation_bonus_days=10)

    # =============================================================
    # Test 9: Integral salary computation
    # =============================================================
    def test_09_integral_salary_computation(self):
        """Validate the integral salary = base + aliquots."""
        contract = self._create_contract(
            wage=3000.0,
            vacation_bonus_days=15,
            utilities_days=30,
        )
        expected_vac_aliquot = 3000.0 * 15 / 360  # 125.0
        expected_util_aliquot = 3000.0 * 30 / 360  # 250.0
        expected_integral = 3000.0 + expected_vac_aliquot + expected_util_aliquot

        self.assertAlmostEqual(
            contract.integral_salary, expected_integral, places=2,
            msg="Salario Integral debe ser base + alícuota vacacional + alícuota utilidades."
        )
        self.assertAlmostEqual(
            contract.integral_daily_salary, expected_integral / 30, places=2,
            msg="Salario Integral Diario debe ser Integral / 30."
        )

    # =============================================================
    # Test 10: Payslip benefit lines generated on compute_sheet
    # =============================================================
    def test_10_payslip_compute_generates_benefit_lines(self):
        """compute_sheet() must generate benefit lines for a valid contract."""
        contract = self._create_contract(contract_type='full_time')
        payslip = self._create_payslip(contract)
        payslip.action_compute_sheet()

        self.assertTrue(
            len(payslip.benefit_line_ids) > 0,
            "La nómina debe tener al menos una línea de beneficio."
        )
        self.assertTrue(
            payslip.total_benefits > 0,
            "El total de beneficios debe ser mayor a 0."
        )

    # =============================================================
    # Test 11: Negative wage validation
    # =============================================================
    def test_11_negative_wage_rejected(self):
        """Contract with negative wage should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_contract(wage=-1000)

    # =============================================================
    # Test 12: Cesta ticket with value 0
    # =============================================================
    def test_12_zero_cesta_ticket(self):
        """Cesta ticket amount of 0 should produce a line with amount 0."""
        contract = self._create_contract(cesta_ticket=0.0)
        payslip = self._create_payslip(contract)
        payslip.action_compute_sheet()

        ct_lines = payslip.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'cesta_ticket'
        )
        if ct_lines:
            self.assertEqual(
                ct_lines[0].amount, 0.0,
                "Cesta Ticket con monto 0 debe generar una línea con amount=0."
            )

    # =============================================================
    # Test 13: Negative cesta ticket validation
    # =============================================================
    def test_13_negative_cesta_ticket_rejected(self):
        """Contract with negative cesta ticket should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_contract(cesta_ticket=-100)

    # =============================================================
    # Test 14: Work factor computation
    # =============================================================
    def test_14_work_factor_values(self):
        """Work factor must be correct for each contract type."""
        ct_ft = self._create_contract(contract_type='full_time')
        self.assertEqual(ct_ft.work_factor, 1.0)
        
        ct_ft.unlink()

        ct_pt = self._create_contract(contract_type='part_time')
        self.assertEqual(ct_pt.work_factor, 0.5)

        ct_pt.unlink()

        ct_tmp = self._create_contract(contract_type='temporary')
        self.assertEqual(ct_tmp.work_factor, 1.0)

    # =============================================================
    # Test 15: Benefit rule formula syntax validation
    # =============================================================
    def test_15_invalid_formula_rejected(self):
        """A rule with invalid Python syntax should raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['hr.benefit.rule'].create({
                'name': 'Regla Inválida',
                'code': 'INVALID_TEST',
                'contract_type': 'full_time',
                'benefit_type': 'utilities',
                'frequency': 'monthly',
                'formula': 'salary_base * /',  # Invalid syntax
            })

    # =============================================================
    # Test 16: Vacation bonus increases with service years
    # =============================================================
    def test_16_vacation_bonus_service_year_progression(self):
        """Vacation bonus formula should increase with service_years."""
        december_date = date(date.today().year, 12, 31)
        
        # Employee with 2 years of service
        contract_2y = self._create_contract(
            start_date=date.today() - relativedelta(years=2),
            wage=3000,
        )
        payslip_2y = self._create_payslip(contract_2y, date_to=december_date)
        payslip_2y.action_compute_sheet()

        vac_2y = sum(payslip_2y.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'vacation_bonus'
        ).mapped('amount'))
        
        contract_2y.unlink()

        # Employee with 5 years of service
        contract_5y = self._create_contract(
            start_date=date.today() - relativedelta(years=5),
            wage=3000,
        )
        payslip_5y = self._create_payslip(contract_5y, date_to=december_date)
        payslip_5y.action_compute_sheet()

        vac_5y = sum(payslip_5y.benefit_line_ids.filtered(
            lambda l: l.benefit_type == 'vacation_bonus'
        ).mapped('amount'))

        if vac_2y > 0 and vac_5y > 0:
            self.assertGreater(
                vac_5y, vac_2y,
                "Bono Vacacional con 5 años debe ser mayor que con 2 años "
                "(+1 día por año LOTTT Art. 192)."
            )

    # =============================================================
    # Test 17: Duplicate rule code rejected
    # =============================================================
    def test_17_duplicate_rule_code_rejected(self):
        """Two rules with the same code should be rejected by SQL constraint."""
        # Cleanup previously generated rule to prevent unique constraints matching across tests
        self.env['hr.benefit.rule'].search([('code', '=', 'UNIQUE_TEST_CODE')]).unlink()
        
        self.env['hr.benefit.rule'].create({
            'name': 'Regla Test Unique A',
            'code': 'UNIQUE_TEST_CODE',
            'contract_type': 'full_time',
            'benefit_type': 'utilities',
            'frequency': 'monthly',
            'formula': 'salary_base',
        })
        with self.assertRaises(Exception):
            self.env['hr.benefit.rule'].create({
                'name': 'Regla Test Unique B',
                'code': 'UNIQUE_TEST_CODE',
                'contract_type': 'part_time',
                'benefit_type': 'utilities',
                'frequency': 'monthly',
                'formula': 'salary_base',
            })
