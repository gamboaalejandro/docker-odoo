# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install', 'account_financial_kpi')
class TestFinancialKpi(AccountTestInvoicingCommon):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # 1. Crear cuentas para nuestra prueba financiera usando tipos fijos Odoo 18
        cls.account_asset = cls.env['account.account'].create({
            'name': 'Banco Ficticio',
            'code': '1010101',
            'account_type': 'asset_current',
            'company_ids': [(4, cls.company_data['company'].id)],
        })
        
        cls.account_liability = cls.env['account.account'].create({
            'name': 'Proveedor Ficticio',
            'code': '2010101',
            'account_type': 'liability_current',
            'company_ids': [(4, cls.company_data['company'].id)],
        })

        # 2. Asentar fondos iniciales creando un asiento contable
        cls.move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': '2026-01-01',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'account_id': cls.account_asset.id, 'debit': 50000.0, 'credit': 0.0}),
                (0, 0, {'account_id': cls.account_liability.id, 'debit': 0.0, 'credit': 50000.0}),
            ]
        })
        cls.move.action_post()

        # 3. Crear el KPI dinámico
        cls.kpi_liquidez = cls.env['account.financial.kpi'].create({
            'name': 'Test Liquidez',
            'formula': 'asset_current / (liability_current * -1)',
            'evaluation_direction': 'higher_is_better',
            'threshold_warning': 1.5,
            'threshold_critical': 0.8
        })

    def test_01_evaluate_formula_engine(self):
        """Verificar que el motor lee y evalúa los saldos contables con precisión."""
        # Liquidez = 50000 / 50000 = 1.0
        self.kpi_liquidez.invalidate_recordset(['current_value', 'state'])
        
        self.assertEqual(self.kpi_liquidez.current_value, 1.0, 
                         "El motor safe_eval calculó mal el balance unificado")
        
        # El threshold_warning es = 1.5 y _critical es = 0.8. Como 1.0 > 0.8 y 1.0 <= 1.5,
        # esto debería dar estado 'warning'
        self.assertEqual(self.kpi_liquidez.state, 'warning', 
                         "Las transiciones de estado para higher_is_better fallaron al evaluar el current_value")

    def test_02_zero_division_safety(self):
        """Previene caídas por error de división por cero"""
        kpi_zero = self.env['account.financial.kpi'].create({
            'name': 'Zero Division Test',
            'formula': 'asset_current / asset_inventory', # No hay inventario, será cero!
            'evaluation_direction': 'higher_is_better',
        })
        # Al acceder al compute, si no explota, pasó.
        self.assertEqual(kpi_zero.current_value, 0.0)

    def test_03_lower_is_better_thresholds(self):
        """Prueba de dirección contraria (PMC u otros factores donde un número mayor es malo)"""
        kpi_pmc = self.env['account.financial.kpi'].create({
            'name': 'Test PMC',
            'formula': 'liability_current * -1', # Resultará ser 50000.0
            'evaluation_direction': 'lower_is_better',
            'threshold_warning': 20000.0,
            'threshold_critical': 60000.0
        })
        # 50000 es >= 20000 y < 60000, estado debe ser warning
        self.assertEqual(kpi_pmc.state, 'warning')
        
        # Incrementar pasivo mediante otro siento, llevando a > 60k
        move_2 = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2026-02-01',
            'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [
                (0, 0, {'account_id': self.account_asset.id, 'debit': 20000.0, 'credit': 0.0}),
                (0, 0, {'account_id': self.account_liability.id, 'debit': 0.0, 'credit': 20000.0}),
            ]
        })
        move_2.action_post()
        
        # Re-evualuar
        kpi_pmc.invalidate_recordset(['current_value', 'state'])
        # Pasivo es ahora 70,000, que es > 60k. Debería ser 'danger' en lower_is_better
        self.assertEqual(kpi_pmc.state, 'danger')
