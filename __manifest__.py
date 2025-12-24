{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '1.0.1',
    'author': 'Alphaqueb Consulting',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas, KPIs y catálogo de fletes marítimos',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/tarifario_views.xml',
        'views/tarifario_menus.xml',
        'views/dashboard_kpi.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'logistica_tarifario/static/src/js/tarifario_dashboard.js',
            'logistica_tarifario/static/src/xml/tarifario_dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}