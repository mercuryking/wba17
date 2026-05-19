{
    'name': '[HDG] Stock Valuation Cost Recalculation',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Recalculate AVCO cost and create adjustment for discrepancies',
    'description': """
        This module allows users to recalculate the Average Cost (AVCO) 
        of products based on historical transactions and create a single 
        valuation adjustment to sync the system value with the calculated value.
    """,
    'author': 'Antigravity',
    'depends': ['stock_account', 'sale_management', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/cost_recalc_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
