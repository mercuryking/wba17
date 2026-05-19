# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name":
    "All In One Cancel - Basic | Cancel Sale Orders | Cancel Purchase Ordrs | Cancel Invoices | Cancel Invenory | Delete Sale Order | Delete Purchase Order | Delete Invoices, Delete Inventory",
    "author":
    "Softhealer Technologies",
    "website":
    "https://www.softhealer.com",
    "support":
    "support@softhealer.com",
    "category":
    "Extra Tools",
    "license":
    "OPL-1",
    "summary":
    "Sale Order Cancel, Cancel Quotation, Purchase Order Cancel, Request For Quotation Cancel, Cancel RFQ, Cancel PO,Delete Invoice, Cancel Payment, Cancel Stock Picking,Cancel Pickings,Delete Inventory Odoo",
    "description":
    """This module helps to cancel sale orders, purchase orders, invoices, payments, stock pickings. You can also cancel multiple records from the tree view.""",
    "version":
    "15.0.4",
    "depends": [
        "account",
        "purchase",
        "sale_management",
        "stock",
        "stock_account",
        "kin_stock_picking_backdate",
    ],
    "application":
    True,
    "data": [
        "security/ir.model.access.csv",

        "sh_account_cancel/security/account_security.xml",
        "sh_account_cancel/data/data.xml",
        "sh_account_cancel/views/res_config_settings.xml",
        "sh_account_cancel/views/views.xml",
        'sh_purchase_cancel/security/purchase_security.xml',
        'sh_purchase_cancel/data/data.xml',
        'sh_purchase_cancel/views/purchase_config_settings.xml',
        'sh_purchase_cancel/views/views.xml',
        'sh_sale_cancel/security/sale_security.xml',
        'sh_sale_cancel/data/data.xml',
        'sh_sale_cancel/views/sale_config_settings.xml',
        'sh_sale_cancel/views/views.xml',
        'sh_stock_cancel/security/stock_security.xml',
        'sh_stock_cancel/data/data.xml',
        'sh_stock_cancel/views/res_config_settings.xml',
        'sh_stock_cancel/views/views.xml',

        "wizard/wizard_cancel_order.xml",
    ],
    "images": [
        'static/description/background.png',
    ],
    "auto_install":
    False,
    "installable":
    True,
    "price":
    80,
    "currency":
    "EUR"
}
