# -*- coding: utf-8 -*-
# from odoo import http


# class WbaCustomAccounting(http.Controller):
#     @http.route('/wba_custom_accounting/wba_custom_accounting', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wba_custom_accounting/wba_custom_accounting/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wba_custom_accounting.listing', {
#             'root': '/wba_custom_accounting/wba_custom_accounting',
#             'objects': http.request.env['wba_custom_accounting.wba_custom_accounting'].search([]),
#         })

#     @http.route('/wba_custom_accounting/wba_custom_accounting/objects/<model("wba_custom_accounting.wba_custom_accounting"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wba_custom_accounting.object', {
#             'object': obj
#         })

