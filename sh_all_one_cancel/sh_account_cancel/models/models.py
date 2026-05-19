# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models,fields


class Payment(models.Model):
    _inherit = 'account.payment'

    cancel_reason = fields.Text('Cancel Reason',tracking=True)


    def action_payment_cancel(self):
        return self.sudo().action_cancel()

    def action_payment_cancel_draft(self):
        return self.sudo().action_draft()
        
    # def action_payment_cancel_delete(self):

    
    def action_cancel(self):
        if not self._context.get('cancel_reason'):
            return {
                'name': 'Cancel Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.cancel.order',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_model': 'account.payment',
                    'default_res_id': str(self.ids),
                    'default_action_name': 'action_cancel',
                },
            }
        cancel_reason = self._context.get('cancel_reason')
        self.write({'cancel_reason': cancel_reason})
        return super(Payment, self).action_cancel()

class Invoice(models.Model):
    _inherit = 'account.move'

    cancel_reason = fields.Text('Cancel Reason',tracking=True)

    def action_invoice_cancel(self):
        return self.sudo().button_cancel()

            

    def action_invoice_cancel_draft(self):
        self.sudo().button_draft()

    def button_cancel(self):
        if not self._context.get('cancel_reason'):
            return {
                'name': 'Cancel Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.cancel.order',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_model': 'account.move',
                    'default_res_id': str(self.ids),
                    'default_action_name': 'button_cancel',
                },
            }
        cancel_reason = self._context.get('cancel_reason')
        self.write({'cancel_reason': cancel_reason})
        return super(Invoice, self).button_cancel()


#     def sh_cancel(self):

#         move = self
#         move_line_ids = move.sudo().mapped('line_ids')
#         reconcile_ids = []
#         if move_line_ids:
#             reconcile_ids = move_line_ids.sudo().mapped('id')
#         reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
#             ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
#         payments = False
#         if reconcile_lines:
#             payments = self.env['account.payment'].search(['|', ('invoice_line_ids.id', 'in', reconcile_lines.mapped(
#                 'credit_move_id').ids), ('invoice_line_ids.id', 'in', reconcile_lines.mapped('debit_move_id').ids)])
#             reconcile_lines.sudo().unlink()

#         if payments:
#             payment_ids = payments
#             if payment_ids.sudo().mapped('move_id').mapped('line_ids'):
#                 payment_lines = payment_ids.sudo().mapped('move_id').mapped('line_ids')
#                 reconcile_ids = payment_lines.sudo().mapped('id')

#                 reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
#                     ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
#                 if reconcile_lines:
#                     reconcile_lines.sudo().unlink()
#                 move.mapped('line_ids.analytic_line_ids').sudo().unlink()

#         if payments:
#             payment_ids = payments
#             payment_ids.sudo().mapped('move_id').write(
#                 {'state': 'draft', 'name': '/'})

#             payment_ids.sudo().mapped('move_id').mapped(
#                 'line_ids').sudo().write({'parent_state': 'draft'})
#             payment_ids.sudo().mapped('move_id').mapped('line_ids').sudo().unlink()

#             if self.company_id.payment_operation_type == 'cancel':
#                 payment_ids.sudo().write({'state': 'cancel'})
#             elif self.company_id.payment_operation_type == 'cancel_draft':
#                 payment_ids.sudo().write({'state': 'cancel'})
#             elif self.company_id.payment_operation_type == 'cancel_delete':
#                 payment_ids.sudo().write({'state': 'cancel'})
# #                 payment_ids.sudo().unlink()

            

#         move_line_ids.sudo().write({'parent_state': 'draft'})
#         move.sudo().write({'state': 'draft'})

#         if self.company_id.invoice_operation_type == 'cancel':
#             self.sudo().write({'state': 'cancel'})
#         elif self.company_id.invoice_operation_type == 'cancel_draft':
#             self.sudo().write({'state': 'draft', 'name': '/'})
#         elif self.company_id.invoice_operation_type == 'cancel_delete':
#             self.sudo().write({'state': 'draft', 'name': '/'})

#         if self.company_id.invoice_operation_type == 'cancel_delete':
#             self.sudo().with_context({'force_delete': True}).unlink()
#             return {
#                 'name': 'Invoices',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'account.move',
#                 'view_type': 'form',
#                 'view_mode': 'tree,kanban,form',
#                 'target': 'current',
#             }
