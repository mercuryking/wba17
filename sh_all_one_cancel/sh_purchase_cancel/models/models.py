# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _check_stock_installed(self):
        stock_app = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'stock')], limit=1)
        if stock_app.state != 'installed':
            return False
        else:
            return True
    
    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search([('name','=','stock_account')],limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True

    def _sh_unreseve_qty(self):
        for move_line in self.sudo().mapped('picking_ids').mapped('move_ids_without_package').mapped('move_line_ids'):
            # unreserve qty
            quant_source = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                        ('product_id', '=',
                                                            move_line.product_id.id),
                                                        ('lot_id', '=', move_line.lot_id.id)], limit=1)
            quant_dest = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                        ('product_id', '=',
                                                            move_line.product_id.id),
                                                        ('lot_id', '=', move_line.lot_id.id)], limit=1)
            if move_line.state == 'done':

                if quant_source:
                    quant_source.write({'quantity': quant_source.quantity + move_line.quantity})


                if quant_dest:
                    quant_dest.write({'quantity': quant_dest.quantity - move_line.quantity})


            elif move_line.state != 'cancel':
                move_line.move_id._do_unreserve()

    def action_purchase_cancel(self):
        for rec in self:
            if rec.company_id.cancel_receipt and self._check_stock_installed():
                if rec.sudo().mapped('picking_ids'):
                    if rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package'):
                        rec.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().write({'state': 'cancel'})
                        rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').mapped(
                            'move_line_ids').sudo().write({'state': 'cancel'})
                    rec._sh_unreseve_qty()
                    rec.sudo().mapped('picking_ids').sudo().write(
                        {'state': 'cancel'})
                    
                    if rec._check_stock_account_installed():
                        
                        # cancel related accouting entries
                        account_move = rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('account_move_ids')
                        account_move_line_ids = account_move.sudo().mapped('line_ids')
                        reconcile_ids = []
                        if account_move_line_ids:
                            reconcile_ids = account_move_line_ids.sudo().mapped('id')
                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                        account_move.sudo().write({'state':'draft','name':'/'})
                        account_move.sudo().with_context({'force_delete':True}).unlink()
                        
                        # cancel stock valuation
                        stock_valuation_layer_ids = rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                        if stock_valuation_layer_ids:
                            stock_valuation_layer_ids.sudo().unlink()

            if rec.company_id.cancel_bill:
                if rec.mapped('invoice_ids'):
                    if rec.mapped('invoice_ids'):
                        move = rec.mapped('invoice_ids')
                        move_line_ids = move.sudo().mapped('line_ids')
                        reconcile_ids = []
                        if move_line_ids:
                            reconcile_ids = move_line_ids.sudo().mapped('id')
                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        payments = False
                        if reconcile_lines:
                            payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                                'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])
                            reconcile_lines.sudo().unlink()
                            if payments:
                                payment_ids = payments
                                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                    reconcile_ids = payment_lines.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        move.mapped(
                            'line_ids.analytic_line_ids').sudo().unlink()

                        move_line_ids.sudo().write({'parent_state': 'draft'})
                        move.sudo().write({'state': 'draft'})
                        if payments:
                            payment_ids = payments

                            payment_ids.sudo().mapped(
                                'move_id').write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped(
                                'line_ids').sudo().write({'parent_state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
                            payment_ids.sudo().write({'state': 'cancel'})

                            payment_ids.sudo().mapped('move_id').with_context(
                                {'force_delete': True}).unlink()

                    rec.mapped('invoice_ids').sudo().write({'state': 'cancel'})
            rec.sudo().write({'state': 'cancel'})

    def action_purchase_cancel_draft(self):
        for rec in self:
            if rec.company_id.cancel_receipt and self._check_stock_installed():
                if rec.sudo().mapped('picking_ids'):
                    if rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package'):
                        rec.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().write({'state': 'draft'})
                        rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').mapped(
                            'move_line_ids').sudo().write({'state': 'draft'})
                    rec._sh_unreseve_qty()

                    if rec._check_stock_account_installed():
                        # cancel related accouting entries
                        account_move = rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('account_move_ids')
                        account_move_line_ids = account_move.sudo().mapped('line_ids')
                        reconcile_ids = []
                        if account_move_line_ids:
                            reconcile_ids = account_move_line_ids.sudo().mapped('id')
                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                        account_move.sudo().write({'state':'draft','name':'/'})
                        account_move.sudo().with_context({'force_delete':True}).unlink()
                        
                        # cancel stock valuation
                        stock_valuation_layer_ids = rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                        if stock_valuation_layer_ids:
                            stock_valuation_layer_ids.sudo().unlink()

                    rec.sudo().mapped('picking_ids').sudo().write(
                        {'state': 'draft'})

            if rec.company_id.cancel_bill:
                if rec.mapped('invoice_ids'):
                    if rec.mapped('invoice_ids'):
                        move = rec.mapped('invoice_ids')
                        move_line_ids = move.sudo().mapped('line_ids')

                        reconcile_ids = []
                        if move_line_ids:
                            reconcile_ids = move_line_ids.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        payments = False
                        if reconcile_lines:
                            payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                                'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                            reconcile_lines.sudo().unlink()

                            if payments:

                                payment_ids = payments
                                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                    reconcile_ids = payment_lines.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        move.mapped(
                            'line_ids.analytic_line_ids').sudo().unlink()

                        move_line_ids.sudo().write({'parent_state': 'draft'})
                        move.sudo().write({'state': 'draft'})

                        if payments:
                            payment_ids = payments
                            payment_ids.sudo().mapped(
                                'move_id').write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped(
                                'line_ids').sudo().write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()
                            payment_ids.sudo().write({'state': 'cancel'})

                            payment_ids.sudo().mapped('move_id').with_context(
                                {'force_delete': True}).unlink()

#                             payment_ids.sudo().unlink()
                    rec.mapped('invoice_ids').sudo().write({'state': 'draft'})
            rec.sudo().write({'state': 'draft'})

    def action_purchase_cancel_delete(self):
        for rec in self:
            if rec.company_id.cancel_receipt and self._check_stock_installed():
                if rec.sudo().mapped('picking_ids'):
                    if rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package'):
                        rec.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().write({'state': 'draft'})
                        rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').mapped(
                            'move_line_ids').sudo().write({'state': 'draft'})
                        rec._sh_unreseve_qty()

                        if rec._check_stock_account_installed():
                            # cancel related accouting entries
                            account_move = rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('account_move_ids')
                            account_move_line_ids = account_move.sudo().mapped('line_ids')
                            reconcile_ids = []
                            if account_move_line_ids:
                                reconcile_ids = account_move_line_ids.sudo().mapped('id')
                            reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                            if reconcile_lines:
                                reconcile_lines.sudo().unlink()
                            account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                            account_move.sudo().write({'state':'draft','name':'/'})
                            account_move.sudo().with_context({'force_delete':True}).unlink()
                            
                            # cancel stock valuation
                            stock_valuation_layer_ids = rec.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                            if stock_valuation_layer_ids:
                                stock_valuation_layer_ids.sudo().unlink()

                        rec.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().unlink()
                        rec.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').mapped('move_line_ids').sudo().unlink()

                    rec.sudo().mapped('picking_ids').sudo().write(
                        {'state': 'draft'})
                    rec.sudo().mapped('picking_ids').sudo().unlink()

            if rec.company_id.cancel_bill:

                if rec.mapped('invoice_ids'):
                    if rec.mapped('invoice_ids'):
                        move = rec.mapped('invoice_ids')
                        move_line_ids = move.sudo().mapped('line_ids')

                        reconcile_ids = []
                        if move_line_ids:
                            reconcile_ids = move_line_ids.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        payments = False
                        if reconcile_lines:
                            payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                                'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                            reconcile_lines.sudo().unlink()

                            if payments:
                                payment_ids = payments
                                if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                    payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                    reconcile_ids = payment_lines.sudo().mapped('id')

                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                            ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        move.mapped(
                            'line_ids.analytic_line_ids').sudo().unlink()

                        move_line_ids.sudo().write({'parent_state': 'draft'})
                        move.sudo().write({'state': 'draft'})

                        if payments:
                            payment_ids = payments
                            payment_ids.sudo().mapped(
                                'move_id').write({'state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped(
                                'line_ids').sudo().write({'parent_state': 'draft'})
                            payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

                            payment_ids.sudo().write({'state': 'cancel'})
#                             payment_ids.sudo().unlink()
                            payment_ids.sudo().mapped('move_id').with_context(
                                {'force_delete': True}).unlink()

                    rec.mapped('invoice_ids').sudo().write({'state': 'draft'})
                    rec.mapped('invoice_ids').sudo().with_context(
                        {'force_delete': True}).unlink()

            rec.sudo().write({'state': 'cancel'})

        for rec in self:
            rec.sudo().unlink()

    def sh_cancel(self):

        if self.company_id.cancel_receipt and self._check_stock_installed():
            if self.company_id.po_operation_type == 'cancel':
                if self.sudo().mapped('picking_ids'):
                    if self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package'):
                        self.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().write({'state': 'cancel'})
                        self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').mapped(
                            'move_line_ids').sudo().write({'state': 'cancel'})
                    self._sh_unreseve_qty()

                    if self._check_stock_account_installed():
                        # cancel related accouting entries
                        account_move = self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('account_move_ids')
                        account_move_line_ids = account_move.sudo().mapped('line_ids')
                        reconcile_ids = []
                        if account_move_line_ids:
                            reconcile_ids = account_move_line_ids.sudo().mapped('id')
                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                        account_move.sudo().write({'state':'draft','name':'/'})
                        account_move.sudo().with_context({'force_delete':True}).unlink()
                        
                        # cancel stock valuation
                        stock_valuation_layer_ids = self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                        if stock_valuation_layer_ids:
                            stock_valuation_layer_ids.sudo().unlink()


                    self.sudo().mapped('picking_ids').sudo().write(
                        {'state': 'cancel'})

            elif self.company_id.po_operation_type == 'cancel_draft':
                if self.sudo().mapped('picking_ids'):
                    if self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package'):
                        self.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().write({'state': 'draft'})
                        self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').mapped(
                            'move_line_ids').sudo().write({'state': 'draft'})
                    self._sh_unreseve_qty()

                    if self._check_stock_account_installed():
                        # cancel related accouting entries
                        account_move = self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('account_move_ids')
                        account_move_line_ids = account_move.sudo().mapped('line_ids')
                        reconcile_ids = []
                        if account_move_line_ids:
                            reconcile_ids = account_move_line_ids.sudo().mapped('id')
                        reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                        if reconcile_lines:
                            reconcile_lines.sudo().unlink()
                        account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                        account_move.sudo().write({'state':'draft','name':'/'})
                        account_move.sudo().with_context({'force_delete':True}).unlink()
                        
                        # cancel stock valuation
                        stock_valuation_layer_ids = self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                        if stock_valuation_layer_ids:
                            stock_valuation_layer_ids.sudo().unlink()


                    self.sudo().mapped('picking_ids').sudo().write(
                        {'state': 'draft'})

            elif self.company_id.po_operation_type == 'cancel_delete':
                if self.sudo().mapped('picking_ids'):
                    if self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package'):
                        self.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().write({'state': 'draft'})
                        self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').mapped(
                            'move_line_ids').sudo().write({'state': 'draft'})
                        self._sh_unreseve_qty()

                        if self._check_stock_account_installed():
                        # cancel related accouting entries
                            account_move = self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('account_move_ids')
                            account_move_line_ids = account_move.sudo().mapped('line_ids')
                            reconcile_ids = []
                            if account_move_line_ids:
                                reconcile_ids = account_move_line_ids.sudo().mapped('id')
                            reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                            if reconcile_lines:
                                reconcile_lines.sudo().unlink()
                            account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                            account_move.sudo().write({'state':'draft','name':'/'})
                            account_move.sudo().with_context({'force_delete':True}).unlink()
                            
                            # cancel stock valuation
                            stock_valuation_layer_ids = self.sudo().mapped('picking_ids').sudo().mapped('move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                            if stock_valuation_layer_ids:
                                stock_valuation_layer_ids.sudo().unlink()


                        self.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').sudo().unlink()
                        self.sudo().mapped('picking_ids').sudo().mapped(
                            'move_ids_without_package').mapped('move_line_ids').sudo().unlink()

                    self.sudo().mapped('picking_ids').sudo().write(
                        {'state': 'draft'})
                    self.sudo().mapped('picking_ids').sudo().unlink()

        if self.company_id.cancel_bill:

            if self.mapped('invoice_ids'):
                if self.mapped('invoice_ids'):
                    move = self.mapped('invoice_ids')
                    move_line_ids = move.sudo().mapped('line_ids')

                    reconcile_ids = []
                    if move_line_ids:
                        reconcile_ids = move_line_ids.sudo().mapped('id')

                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    payments = False
                    if reconcile_lines:
                        payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
                            'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])

                        reconcile_lines.sudo().unlink()

                        if payments:
                            payment_ids = payments
                            if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
                                payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
                                reconcile_ids = payment_lines.sudo().mapped('id')

                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    move.mapped('line_ids.analytic_line_ids').sudo().unlink()

                    move_line_ids.sudo().write({'parent_state': 'draft'})
                    move.sudo().write({'state': 'draft'})

                    if payments:
                        payment_ids = payments
                        payment_ids.sudo().mapped(
                            'move_id').write({'state': 'draft'})
                        payment_ids.sudo().mapped('move_id').mapped(
                            'line_ids').sudo().write({'parent_state': 'draft'})
                        payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

                        if self.company_id.po_operation_type == 'cancel':
                            payment_ids.sudo().write({'state': 'cancel'})
                        elif self.company_id.po_operation_type == 'cancel_draft':
                            payment_ids.sudo().write({'state': 'cancel'})
#                             payment_ids.sudo().unlink()
                        elif self.company_id.po_operation_type == 'cancel_delete':
                            payment_ids.sudo().write({'state': 'cancel'})
#                             payment_ids.sudo().unlink()

                        payment_ids.sudo().mapped('move_id').with_context(
                            {'force_delete': True}).unlink()

                if self.company_id.po_operation_type == 'cancel':
                    self.mapped('invoice_ids').sudo().write(
                        {'state': 'cancel'})
                elif self.company_id.po_operation_type == 'cancel_draft':
                    self.mapped('invoice_ids').sudo().write(
                        {'state': 'draft', 'name': '/'})
                elif self.company_id.po_operation_type == 'cancel_delete':
                    self.mapped('invoice_ids').sudo().write(
                        {'state': 'draft', 'name': '/'})
                    self.mapped('invoice_ids').sudo().with_context(
                        {'force_delete': True}).unlink()

        if self.company_id.po_operation_type == 'cancel':
            self.sudo().write({'state': 'cancel'})
        elif self.company_id.po_operation_type == 'cancel_draft':
            self.sudo().write({'state': 'draft'})
        elif self.company_id.po_operation_type == 'cancel_delete':
            self.sudo().write({'state': 'cancel'})
            self.sudo().unlink()
            return {
                'name': 'Purchase Order',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_type': 'form',
                'view_mode': 'tree,kanban,form,pivot,graph,calendar,activity',
                'target': 'current',
                'context': {}
            }
