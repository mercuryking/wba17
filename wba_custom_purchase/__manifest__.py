# -*- coding: utf-8 -*-
{
    'name': "wba - Custom Purchase",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase_stock', 'stock_account', 'delivery'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',




        'views/purchase_order.xml',
        'views/purchase_order_category.xml',
        
        'report/purchase_order.xml',
        'report/purchase_order_non_ttd.xml',

        'wizard/choose_delivery_carrier_purchase_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

