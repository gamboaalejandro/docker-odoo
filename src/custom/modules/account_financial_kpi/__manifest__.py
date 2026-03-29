# -*- coding: utf-8 -*-
{
    'name': 'Tablero de Salud Financiera',
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'summary': 'Tablero Kanban de Indicadores Financieros Configurables (KPI)',
    'description': """
        Módulo para crear indicadores de salud financiera (KPI) mediante fórmulas dinámicas seguras y umbrales.
        Permite a la gerencia y contadores visualizar en un Dashboard tipo Kanban el estado de sus finanzas
        con colores semaforizados.
    """,
    'author': 'Binaural',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_financial_kpi_views.xml',
        'data/kpi_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
