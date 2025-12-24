{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '1.0.1',
    'author': 'Expert Developer',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas, KPIs y catálogo de fletes marítimos',
    'depends': ['base', 'web', 'board'],
    'data': [
        'security/ir.model.access.csv',
        'views/tarifario_menus.xml',
        'views/tarifario_views.xml',
        'views/dashboard_kpi.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'logistica_tarifario/static/src/css/tarifario_style.css',
            'logistica_tarifario/static/src/js/tarifario_dashboard.js',
            'logistica_tarifario/static/src/xml/tarifario_dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
