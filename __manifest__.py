{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '19.0.3.2.3',
    'author': 'Alphaqueb Consulting',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas y catálogo editable de fletes marítimos',
    # purchase_stock es OBLIGATORIO: la vista de la OC ancla xpaths a campos
    # que ESE módulo inyecta (picking_type_id, effective_date). Sin la
    # dependencia, este módulo carga antes ('l' < 'p' a igual profundidad) y
    # la validación truena con "no se puede localizar" (2026-08-10).
    'depends': ['base', 'mail', 'contacts', 'purchase', 'stock', 'purchase_stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/partner_category_data.xml',
        'data/tarifario_month_data.xml',
        'views/tarifario_views.xml',
        'views/purchase_order_views.xml',
        'views/tarifario_menus.xml',
        'views/dashboard_kpi.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}