{
    'name': 'Nómina Venezuela - Cálculo Automático de Beneficios',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Cálculo automático de beneficios laborales según la LOTTT venezolana',
    'description': """
        Módulo de nómina para Venezuela (LOTTT).
        =========================================
        - Tipo de contrato venezolano (Tiempo Completo, Medio Tiempo, Temporal).
        - Tabla de reglas de beneficios configurable.
        - Cálculo automático de: Utilidades, Bono Vacacional,
          Prestaciones Sociales (Garantía), Cesta Ticket.
        - Salario Integral con alícuotas según legislación vigente.
        - Aplicación automática de beneficios al generar nómina.
    """,
    'author': 'Alejandro Gamboa',
    'website': '',
    'depends': ['hr', 'hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'data/benefit_rules_data.xml',
        'views/hr_benefit_rule_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
