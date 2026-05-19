from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_sh_cancel(self):
        for order in self:
            # 1. Reset Pickings
            if order.picking_ids:
                order.picking_ids.action_force_reset_draft()
                order.picking_ids.action_cancel()
            
            # 2. Reset Invoices (Draft then Cancel)
            if order.invoice_ids:
                for inv in order.invoice_ids:
                    if inv.state != 'cancel':
                        inv.button_draft()
                        inv.button_cancel()
            
            # 3. Cancel Order
            order.action_cancel()
        return True

    def action_sh_reset_to_draft(self):
        for order in self:
            order.action_sh_cancel()
            order.action_draft()
        return True
