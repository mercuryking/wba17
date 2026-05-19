# -*- coding: utf-8 -*-
{
    'name': "wba - Custom Accounting",

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
    'depends': ['base', 'account', 'sale', 'purchase'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings.xml',
        'views/account_move.xml',

        'report/invoice_report_a4.xml',
        'report/invoice_report_a5_new.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

