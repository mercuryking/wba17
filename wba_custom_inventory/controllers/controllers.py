# -*- coding: utf-8 -*-
# from odoo import http


# class WbaCustomInventory(http.Controller):
#     @http.route('/wba_custom_inventory/wba_custom_inventory', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wba_custom_inventory/wba_custom_inventory/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wba_custom_inventory.listing', {
#             'root': '/wba_custom_inventory/wba_custom_inventory',
#             'objects': http.request.env['wba_custom_inventory.wba_custom_inventory'].search([]),
#         })

#     @http.route('/wba_custom_inventory/wba_custom_inventory/objects/<model("wba_custom_inventory.wba_custom_inventory"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wba_custom_inventory.object', {
#             'object': obj
#         })

