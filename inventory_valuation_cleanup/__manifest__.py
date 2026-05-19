{
    'name': '[HDG] Inventory Valuation Cleanup',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Clean up residual valuation for products with zero quantity',
    'description': """
        This module provides a wizard to identify and clean up residual inventory valuation
        balances for products that have zero physical quantity.
    """,
    'author': 'Antigravity',
    'depends': ['stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/valuation_cleanup_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
