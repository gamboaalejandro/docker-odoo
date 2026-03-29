from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestAccountDiscountRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountDiscountRules, cls).setUpClass()
        # Clean up existing rules to have a clean slate
        cls.env['account.discount.rule'].search([]).unlink()

        # Create Products
        cls.product_a = cls.env['product.product'].create({'name': 'Producto A', 'list_price': 100.0})
        cls.product_b = cls.env['product.product'].create({'name': 'Producto B', 'list_price': 200.0})

        # Create Partners
        cls.partner_retail = cls.env['res.partner'].create({'name': 'Cliente Minorista', 'customer_type': 'retail'})
        cls.partner_wholesale = cls.env['res.partner'].create({'name': 'Cliente Mayorista', 'customer_type': 'wholesale'})
        cls.partner_vip = cls.env['res.partner'].create({'name': 'Cliente VIP', 'customer_type': 'vip'})
        cls.partner_special = cls.env['res.partner'].create({'name': 'Cliente Especial', 'customer_type': 'vip'})

        # Setup Account Journal
        cls.journal = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)

        # Basic Rules
        cls.rule_wholesale = cls.env['account.discount.rule'].create({
            'name': '10% Mayoristas',
            'sequence': 50,
            'customer_type': 'wholesale',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
        })
        cls.rule_vip_general = cls.env['account.discount.rule'].create({
            'name': '15% VIP',
            'sequence': 40,
            'customer_type': 'vip',
            'discount_type': 'percentage',
            'discount_percentage': 15.0,
        })
        cls.rule_vip_product_a = cls.env['account.discount.rule'].create({
            'name': '25% VIP en Producto A',
            'sequence': 30,
            'customer_type': 'vip',
            'product_id': cls.product_a.id,
            'discount_type': 'percentage',
            'discount_percentage': 25.0,
        })

    def _create_invoice(self, partner, product, quantity=1, price_unit=None):
        """Helper to create an unposted invoice with a single line."""
        if price_unit is None:
            price_unit = product.list_price
        
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': product.id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                })
            ],
        })
        return move

    def test_01_wholesale_general_discount(self):
        """Test that wholesale customer gets generic 10% discount."""
        invoice = self._create_invoice(self.partner_wholesale, self.product_b)
        invoice.action_post()
        
        line = invoice.invoice_line_ids[0]
        self.assertEqual(line.discount, 10.0, "El cliente mayorista debería recibir un 10% de descuento.")
        self.assertEqual(invoice.state, 'posted', "La factura debería estar publicada.")

    def test_02_vip_product_priority(self):
        """Test that product-specific rule overrides generic type rule based on sequence."""
        invoice = self._create_invoice(self.partner_vip, self.product_a)
        invoice.action_post()
        
        line = invoice.invoice_line_ids[0]
        # VIP general is 40 (15%), VIP product A is 30 (25%) -> Product specific should apply
        self.assertEqual(line.discount, 25.0, "La regla de producto específico debería tener prioridad sobre la general.")

    def test_03_partner_specific_rule(self):
        """Test that partner-specific rule works and overrides general."""
        self.env['account.discount.rule'].create({
            'name': '50% Especial Exclusivo',
            'sequence': 10,
            'partner_id': self.partner_special.id,
            'discount_type': 'percentage',
            'discount_percentage': 50.0,
        })
        
        invoice = self._create_invoice(self.partner_special, self.product_b)
        invoice.action_post()
        
        line = invoice.invoice_line_ids[0]
        self.assertEqual(line.discount, 50.0, "La regla de partner específico debería aplicar y tener prioridad.")

    def test_04_retail_no_discount(self):
        """Test that a customer with no matching rules gets 0 discount."""
        invoice = self._create_invoice(self.partner_retail, self.product_b)
        invoice.action_post()
        
        line = invoice.invoice_line_ids[0]
        self.assertEqual(line.discount, 0.0, "Minoristas no deberían tener descuento si no hay regla.")

    def test_05_dynamic_formula(self):
        """Test discount applied dynamically via formula."""
        self.env['account.discount.rule'].create({
            'name': 'Fórmula VIP Volumen',
            'sequence': 5, # Highest priority
            'customer_type': 'vip',
            'discount_type': 'formula',
            'discount_formula': 'result = 30.0 if line.quantity > 5 else 5.0'
        })
        
        # Less than 5 quantity -> 5%
        inv1 = self._create_invoice(self.partner_vip, self.product_b, quantity=2)
        inv1.action_post()
        self.assertEqual(inv1.invoice_line_ids[0].discount, 5.0)

        # More than 5 quantity -> 30%
        inv2 = self._create_invoice(self.partner_vip, self.product_b, quantity=10)
        inv2.action_post()
        self.assertEqual(inv2.invoice_line_ids[0].discount, 30.0)

    def test_06_invalid_formula(self):
        """Test that invalid formula raises validation error on rule creation."""
        with self.assertRaises(ValidationError):
            self.env['account.discount.rule'].create({
                'name': 'Mala Formula',
                'discount_type': 'formula',
                'discount_formula': 'syntax error python / / '
            })

    def test_07_multiple_lines_invoice(self):
        """Test an invoice with multiple lines where rules match differently."""
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_vip.id,
            'journal_id': self.journal.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product_a.id, 'quantity': 1, 'price_unit': 100}),
                (0, 0, {'product_id': self.product_b.id, 'quantity': 1, 'price_unit': 200}),
            ],
        })
        move.action_post()

        line_a = move.invoice_line_ids.filtered(lambda l: l.product_id == self.product_a)
        line_b = move.invoice_line_ids.filtered(lambda l: l.product_id == self.product_b)

        # line A -> VIP + Product A = 25% (seq 30)
        # line B -> VIP + general = 15% (seq 40)
        self.assertEqual(line_a.discount, 25.0)
        self.assertEqual(line_b.discount, 15.0)
