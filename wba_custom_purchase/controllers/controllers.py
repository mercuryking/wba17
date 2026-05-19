# -*- coding: utf-8 -*-
# from odoo import http


# class WbaCustomPurchase(http.Controller):
#     @http.route('/wba_custom_purchase/wba_custom_purchase', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wba_custom_purchase/wba_custom_purchase/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wba_custom_purchase.listing', {
#             'root': '/wba_custom_purchase/wba_custom_purchase',
#             'objects': http.request.env['wba_custom_purchase.wba_custom_purchase'].search([]),
#         })

#     @http.route('/wba_custom_purchase/wba_custom_purchase/objects/<model("wba_custom_purchase.wba_custom_purchase"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wba_custom_purchase.object', {
#             'object': obj
#         })

