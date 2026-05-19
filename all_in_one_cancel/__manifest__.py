{
    'name': '[HDG] All In One Cancel (Odoo 17)',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Smart cancel for Sale, Purchase and Inventory with Stock focus',
    'description': """
        Modern cancellation module for Odoo 17. 
        Focuses on resetting inventory pickings and valuation correctly.
    """,
    'author': 'Antigravity',
    'depends': ['sale_management', 'purchase', 'stock_account'],
    'data': [
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
