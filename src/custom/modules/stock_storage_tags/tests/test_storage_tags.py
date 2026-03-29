# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install', 'stock_storage_tags')
class TestStorageTags(common.TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super(TestStorageTags, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Crear algunas etiquetas de prueba
        cls.tag_fragil = cls.env['stock.storage.tag'].create({
            'name': 'Frágil',
            'color': 1,
            'description': 'Manejar con cuidado'
        })
        cls.tag_peligroso = cls.env['stock.storage.tag'].create({
            'name': 'Peligroso',
            'color': 2,
        })
        
        # Crear un producto (Plantilla)
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Ácido Sulfúrico',
            'type': 'product'
        })

        # Al crearse el template con una variante única, Odoo crea la variante:
        cls.product_variant = cls.product_tmpl.product_variant_ids[0]

    def test_01_tag_creation(self):
        """Validar la creación y constraints de las etiquetas."""
        self.assertEqual(self.tag_fragil.name, 'Frágil')
        self.assertEqual(self.tag_peligroso.color, 2)
        
    def test_02_assign_via_wizard_template(self):
        """Simular la carga del wizard y escritura en la plantilla de producto."""
        wizard = self.env['product.tag.wizard'].with_context(
            active_model='product.template',
            active_id=self.product_tmpl.id
        ).create({})

        # Asignar etiquetas desde el entorno del wizard
        wizard.storage_tag_ids = [(6, 0, [self.tag_fragil.id, self.tag_peligroso.id])]
        wizard.action_apply_tags()

        # Comprobar que el producto plantilla tiene las etiquetas
        self.assertIn(self.tag_fragil, self.product_tmpl.storage_tag_ids)
        self.assertIn(self.tag_peligroso, self.product_tmpl.storage_tag_ids)
        self.assertEqual(len(self.product_tmpl.storage_tag_ids), 2)

    def test_03_assign_via_wizard_variant(self):
        """Simular la asignación directa sobre la variante de producto."""
        wizard_var = self.env['product.tag.wizard'].with_context(
            active_model='product.product',
            active_id=self.product_variant.id
        ).create({})

        # Asignar solo una etiqueta a la variante
        wizard_var.storage_tag_ids = [(6, 0, [self.tag_peligroso.id])]
        wizard_var.action_apply_tags()

        # Verificar que se escribió la relación Many2many en la variante
        self.assertIn(self.tag_peligroso, self.product_variant.storage_tag_ids)
        self.assertNotIn(self.tag_fragil, self.product_variant.storage_tag_ids)

    def test_04_search_filtering(self):
        """Validar que el motor de búsqueda ORM puede filtrar productos por M2M de etiquetas."""
        # Se aplican las dos etiquetas al producto plantilla
        self.product_tmpl.storage_tag_ids = [(6, 0, [self.tag_fragil.id, self.tag_peligroso.id])]
        
        # Crear otro producto sin la etiqueta "Peligroso"
        prod2 = self.env['product.template'].create({
            'name': 'Copas de Cristal',
            'storage_tag_ids': [(6, 0, [self.tag_fragil.id])]
        })

        # Búsqueda de productos "Frágiles" -> deberían ser ambos
        fragiles = self.env['product.template'].search([('storage_tag_ids', 'in', self.tag_fragil.ids)])
        self.assertIn(self.product_tmpl, fragiles)
        self.assertIn(prod2, fragiles)

        # Búsqueda de productos "Peligrosos" -> solo el Ácido Sulfúrico
        peligrosos = self.env['product.template'].search([('storage_tag_ids', 'in', self.tag_peligroso.ids)])
        self.assertIn(self.product_tmpl, peligrosos)
        self.assertNotIn(prod2, peligrosos)
