# -*- coding: utf-8 -*-
# from odoo import http


# class AccountReportsGlByDate(http.Controller):
#     @http.route('/account_reports_gl_by_date/account_reports_gl_by_date', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_reports_gl_by_date/account_reports_gl_by_date/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_reports_gl_by_date.listing', {
#             'root': '/account_reports_gl_by_date/account_reports_gl_by_date',
#             'objects': http.request.env['account_reports_gl_by_date.account_reports_gl_by_date'].search([]),
#         })

#     @http.route('/account_reports_gl_by_date/account_reports_gl_by_date/objects/<model("account_reports_gl_by_date.account_reports_gl_by_date"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_reports_gl_by_date.object', {
#             'object': obj
#         })

