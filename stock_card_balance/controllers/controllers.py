# -*- coding: utf-8 -*-
# from odoo import http


# class StockCardBalance(http.Controller):
#     @http.route('/stock_card_balance/stock_card_balance', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_card_balance/stock_card_balance/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_card_balance.listing', {
#             'root': '/stock_card_balance/stock_card_balance',
#             'objects': http.request.env['stock_card_balance.stock_card_balance'].search([]),
#         })

#     @http.route('/stock_card_balance/stock_card_balance/objects/<model("stock_card_balance.stock_card_balance"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_card_balance.object', {
#             'object': obj
#         })
