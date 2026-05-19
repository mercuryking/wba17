from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import date

_logger = logging.getLogger(__name__)

class CostRecalcWizard(models.TransientModel):
    _name = 'valuation.cost.recalc.wizard'
    _description = 'Valuation Cost Recalculation Wizard'

    product_ids = fields.Many2many('product.product', string='Products', required=True)
    start_date = fields.Date(string='Start Date', required=True, 
                            default=lambda self: date(date.today().year, 1, 1))
    counterpart_account_id = fields.Many2one('account.account', string='Counterpart Account', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, 
                                domain=[('type', '=', 'general')])
    reason = fields.Char(string='Reason', default='Cost Revalidation Adjustment')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        
        if active_ids and active_model == 'product.product':
            res['product_ids'] = [(6, 0, active_ids)]
        elif active_ids and active_model == 'stock.valuation.layer':
            svls = self.env['stock.valuation.layer'].browse(active_ids)
            product_ids = svls.mapped('product_id').ids
            res['product_ids'] = [(6, 0, product_ids)]
        return res

    def action_recalculate(self):
        self.ensure_one()
        created_move_ids = []
        products_processed = 0
        
        for product in self.product_ids:
            if product.company_id and product.company_id != self.env.company:
                continue

            # Get initial balance before start_date
            start_dt = fields.Datetime.from_string(str(self.start_date) + " 00:00:00")
            initial_svls = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id),
                ('create_date', '<', start_dt),
                ('company_id', '=', self.env.company.id)
            ])
            current_sim_qty = sum(initial_svls.mapped('quantity'))
            current_sim_value = sum(initial_svls.mapped('value'))
            current_avg_cost = current_sim_value / current_sim_qty if current_sim_qty > 0 else 0.0

            # Re-fetch moves with strict ordering
            moves = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('company_id', '=', self.env.company.id),
                ('date', '>=', self.start_date)
            ], order='date asc, id asc')

            for move in moves:
                svls = move.stock_valuation_layer_ids
                move_value = sum(svls.mapped('value'))
                qty_done = sum(svls.mapped('quantity')) # Use SVL qty for accuracy
                
                if move._is_in():
                    current_sim_qty += qty_done
                    current_sim_value += move_value
                    if current_sim_qty > 0:
                        current_avg_cost = current_sim_value / current_sim_qty
                elif move._is_out():
                    # Consumption uses the current average cost, except for vendor returns
                    if move.origin_returned_move_id:
                        out_val = move_value
                    else:
                        out_val = qty_done * current_avg_cost # qty_done is negative for OUT
                    current_sim_qty += qty_done
                    current_sim_value += out_val
            
            odoo_value = product.value_svl
            diff_value = current_sim_value - odoo_value

            if abs(diff_value) > 0.01:
                svl_vals = {
                    'product_id': product.id,
                    'value': diff_value,
                    'quantity': 0,
                    'description': self.reason,
                    'company_id': self.env.company.id,
                }
                new_svl = self.env['stock.valuation.layer'].sudo().create(svl_vals)
                move = self._create_account_move(product, diff_value, new_svl)
                created_move_ids.append(move.id)
                
                product.sudo().with_context(do_not_create_svl=True).write({'standard_price': current_avg_cost})
                products_processed += 1

        if not created_move_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Adjustment Needed'),
                    'message': _('The valuation is already accurate.'),
                    'sticky': False,
                }
            }

        # Return an action to open the created moves
        return {
            'name': _('Draft Adjustments Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_move_ids)],
            'target': 'current',
        }

    def _create_account_move(self, product, value, svl):
        # Implementation of draft journal entry creation
        # Logic to find valuation account etc.
        valuation_account = product.categ_id.property_stock_valuation_account_id
        if not valuation_account:
            raise UserError(_("No valuation account defined for product category %s") % product.categ_id.name)
            
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.reason + ': ' + product.name,
            'move_type': 'entry',
            'stock_valuation_layer_ids': [(4, svl.id)],
            'line_ids': [
                (0, 0, {
                    'name': self.reason,
                    'account_id': valuation_account.id,
                    'debit': value if value > 0 else 0,
                    'credit': -value if value < 0 else 0,
                }),
                (0, 0, {
                    'name': self.reason,
                    'account_id': self.counterpart_account_id.id,
                    'debit': -value if value < 0 else 0,
                    'credit': value if value > 0 else 0,
                }),
            ]
        }
        return self.env['account.move'].sudo().create(move_vals)
