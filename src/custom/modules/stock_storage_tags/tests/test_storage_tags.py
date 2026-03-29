# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from psycopg2 import IntegrityError
from odoo.tools import mute_logger
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
            'type': 'consu'
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


    def test_05_prevent_duplicate_tags(self):
        """Verifica que no se puedan crear dos etiquetas con el mismo nombre"""
        self.env['stock.storage.tag'].create({
            'name': 'Zona Peligrosa',
            'color': 1
        })
        
        # mute_logger evita que el error esperado ensucie el log de la terminal
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['stock.storage.tag'].create({
                'name': 'Zona Peligrosa', # Nombre idéntico
                'color': 2
            })
    def test_06_tag_deletion_cascade(self):
        """Verifica que al borrar una etiqueta, el producto no se vea afectado, solo se desvincule"""
        # Crear etiqueta y producto
        tag = self.env['stock.storage.tag'].create({'name': 'Baja Rotación'})
        product = self.env['product.template'].create({
            'name': 'Producto de Prueba Borrado',
            'storage_tag_ids': [(4, tag.id)]
        })
        
        self.assertIn(tag, product.storage_tag_ids)
        
        # Eliminar la etiqueta
        tag.unlink()
        
        # Validar que el producto sigue existiendo pero ya no tiene la etiqueta
        self.assertTrue(product.exists(), "El producto no debió borrarse.")
        self.assertFalse(product.storage_tag_ids, "La relación debió limpiarse al borrar la etiqueta.")

    def test_07_wizard_clear_all_tags(self):
        """Verifica que el wizard pueda eliminar todas las etiquetas de un producto si se envía vacío"""
        # Asignamos una etiqueta inicialmente
        tag = self.env['stock.storage.tag'].create({'name': 'Temporal'})
        self.product_tmpl.storage_tag_ids = [(6, 0, [tag.id])]
        self.assertTrue(self.product_tmpl.storage_tag_ids)
        
        # Simulamos la ejecución del wizard dejando el campo de etiquetas vacío
        wizard = self.env['product.tag.wizard'].with_context(
            active_model='product.template',
            active_id=self.product_tmpl.id
        ).create({
            'storage_tag_ids': [(5, 0, 0)] # El comando 5 limpia el Many2Many
        })
        wizard.action_apply_tags()
        
        # Validamos que el producto ya no tenga etiquetas
        self.assertFalse(self.product_tmpl.storage_tag_ids, "El wizard debió limpiar todas las etiquetas del producto.")