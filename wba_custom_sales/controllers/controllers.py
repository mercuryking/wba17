# -*- coding: utf-8 -*-
# from odoo import http


# class WbaCustomSales(http.Controller):
#     @http.route('/wba_custom_sales/wba_custom_sales', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wba_custom_sales/wba_custom_sales/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wba_custom_sales.listing', {
#             'root': '/wba_custom_sales/wba_custom_sales',
#             'objects': http.request.env['wba_custom_sales.wba_custom_sales'].search([]),
#         })

#     @http.route('/wba_custom_sales/wba_custom_sales/objects/<model("wba_custom_sales.wba_custom_sales"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wba_custom_sales.object', {
#             'object': obj
#         })

