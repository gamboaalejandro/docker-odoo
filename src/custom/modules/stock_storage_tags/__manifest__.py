# -*- coding: utf-8 -*-
{
    'name': 'Stock Storage Tags',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Etiquetas Inteligentes de Almacenamiento',
    'description': """
        Permite asignar etiquetas dinámicas a productos y variantes para 
        mejorar la organización visual y operativa en los almacenes.
        
        Características:
        * Etiquetas M2M en Plantillas y Variantes.
        * Propagación visual a Movimientos de Stock.
        * Agrupación automática en la vista Kanban.
        * Asignación rápida mediante Wizard.
    """,
    'author': 'Binaural',
    'depends': ['stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_tag_wizard_views.xml',
        'views/stock_storage_tag_views.xml',
        'views/product_views.xml',
        'views/stock_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
