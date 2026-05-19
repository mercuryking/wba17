from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ValuationCleanupWizard(models.TransientModel):
    _name = 'valuation.cleanup.wizard'
    _description = 'Inventory Valuation Cleanup Wizard'

    line_ids = fields.One2many('valuation.cleanup.line', 'wizard_id', string='Products to Cleanup')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 domain=[('type', '=', 'general')],
                                 default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1))
    date = fields.Date(string='Cleanup Date', required=True, default=fields.Date.today)
    account_id = fields.Many2one('account.account', string='Counterpart Account', required=True,
                                 domain=[('deprecated', '=', False)],
                                 help="The account that will be used as the counterpart to the Stock Valuation account.")

    def action_scan(self):
        self.line_ids.unlink()
        lines = []
        # Find products with zero quantity but non-zero valuation
        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)
        ])
        for product in products:
            # We use value_svl which is the sum of all valuation layers
            total_value = product.value_svl
            if product.qty_available == 0 and not self.env.company.currency_id.is_zero(total_value):
                lines.append((0, 0, {
                    'product_id': product.id,
                    'current_value': total_value,
                    'fix': True,
                }))
        self.write({'line_ids': lines})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'valuation.cleanup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply(self):
        for line in self.line_ids.filtered(lambda l: l.fix):
            product = line.product_id
            diff_value = -line.current_value
            
            # 1. Create Valuation Layer
            svl = self.env['stock.valuation.layer'].create({
                'product_id': product.id,
                'quantity': 0,
                'value': diff_value,
                'remaining_qty': 0,
                'company_id': self.env.company.id,
                'description': _('Valuation Cleanup (Zero Qty)'),
            })
            # Odoo doesn't allow setting create_date easily, so we might need to update it via SQL or just rely on the Account Move date for financial reports.
            # However, in Odoo 17, SVL has a 'create_date' but we usually use the 'account_move' date for fiscal reporting.

            # 2. Create Account Move if automated
            if product.valuation == 'real_time':
                accounts = product.product_tmpl_id.get_product_accounts()
                inventory_account = accounts.get('stock_valuation')
                # Use the account selected in the wizard
                adjustment_account = self.account_id
                
                if not inventory_account or not adjustment_account:
                    raise UserError(_("Please configure stock valuation/adjustment accounts for product %s") % product.name)

                move_vals = {
                    'journal_id': self.journal_id.id,
                    'date': self.date,
                    'company_id': self.env.company.id,
                    'ref': _('Valuation Cleanup: %s') % product.name,
                    'stock_valuation_layer_ids': [(4, svl.id)],
                    'line_ids': [
                        (0, 0, {
                            'name': _('Valuation Cleanup: %s') % product.name,
                            'account_id': inventory_account.id,
                            'debit': diff_value if diff_value > 0 else 0,
                            'credit': -diff_value if diff_value < 0 else 0,
                        }),
                        (0, 0, {
                            'name': _('Valuation Cleanup: %s') % product.name,
                            'account_id': adjustment_account.id,
                            'debit': -diff_value if diff_value < 0 else 0,
                            'credit': diff_value if diff_value > 0 else 0,
                        }),
                    ],
                }
                move = self.env['account.move'].create(move_vals)
                # Left as DRAFT for review as per recommendations
                svl.write({'account_move_id': move.id})

        return {'type': 'ir.actions.client', 'tag': 'reload'}

class ValuationCleanupLine(models.TransientModel):
    _name = 'valuation.cleanup.line'
    _description = 'Valuation Cleanup Line'

    wizard_id = fields.Many2one('valuation.cleanup.wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    current_value = fields.Float(string='Current Value', readonly=True)
    fix = fields.Boolean(string='Fix?', default=True)
