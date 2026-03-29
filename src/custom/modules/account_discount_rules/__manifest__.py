# -*- coding: utf-8 -*-
{
    'name': 'Account Discount Rules',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Policy-based automatic discount rules for invoices',
    'description': """
        This module allows configuration of advanced discount rules on invoices based on:
        - Customer Type (Retail, Wholesale, VIP)
        - Specific Customer
        - Specific Product
        - Dynamic Formulas or Fixed Percentages
    """,
    'author': 'Binaural',
    'depends': ['account', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_discount_rule_views.xml',
        'views/res_partner_views.xml',
        'data/discount_rules_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
