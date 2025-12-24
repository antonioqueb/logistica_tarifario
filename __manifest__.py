{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '1.0.1',
    'author': 'Expert Developer',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas, KPIs y catálogo de fletes marítimos',
    'depends': ['base', 'web', 'board', 'mail'], # He añadido 'mail' porque usas _inherit mail.thread
    'data': [
        'security/ir.model.access.csv',
        'views/tarifario_views.xml',     # 1. CARGA PRIMERO (Define la acción)
        'views/tarifario_menus.xml',     # 2. CARGA DESPUÉS (Usa la acción)
        'views/dashboard_kpi.xml',       # 3. CARGA AL FINAL (Usa los menús raíz)
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