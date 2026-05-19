from odoo import models, fields, api, _
from datetime import date
import calendar
import logging

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def cron_auto_cleanup_valuation(self):
        """Scheduled action to cleanup valuation for zero-qty products"""
        # Find a default journal and account
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        # We need a default counterpart account. 
        # Typically we use 'Inventory Adjustment' or 'Price Difference'
        # For this cron, we'll try to find an appropriate account or use a fallback.
        
        products_to_fix = self.search([('type', '=', 'product')])
        
        for product in products_to_fix:
            try:
                total_value = product.value_svl
                if product.qty_available == 0 and not self.env.company.currency_id.is_zero(total_value):
                    # Process cleanup
                    diff_value = -total_value
                    
                    # 1. Create SVL
                    svl = self.env['stock.valuation.layer'].create({
                        'product_id': product.id,
                        'quantity': 0,
                        'value': diff_value,
                        'remaining_qty': 0,
                        'company_id': self.env.company.id,
                        'description': _('Auto Cleanup (Zero Qty) - Scheduled'),
                    })

                    # 2. Create Account Move (Draft)
                    if product.valuation == 'real_time':
                        accounts = product.product_tmpl_id.get_product_accounts()
                        inventory_account = accounts.get('stock_valuation')
                        
                        # Use price difference account or fallback to output account
                        adjustment_account = product.categ_id.property_account_creditor_price_difference or \
                                             product.categ_id.property_stock_account_output_categ_id
                        
                        if inventory_account and adjustment_account and journal:
                            move_vals = {
                                'journal_id': journal.id,
                                'date': fields.Date.today(),
                                'company_id': self.env.company.id,
                                'ref': _('Auto Valuation Cleanup: %s') % product.name,
                                'stock_valuation_layer_ids': [(4, svl.id)],
                                'line_ids': [
                                    (0, 0, {
                                        'name': _('Auto Cleanup: %s') % product.name,
                                        'account_id': inventory_account.id,
                                        'debit': diff_value if diff_value > 0 else 0,
                                        'credit': -diff_value if diff_value < 0 else 0,
                                    }),
                                    (0, 0, {
                                        'name': _('Auto Cleanup: %s') % product.name,
                                        'account_id': adjustment_account.id,
                                        'debit': -diff_value if diff_value < 0 else 0,
                                        'credit': diff_value if diff_value > 0 else 0,
                                    }),
                                ],
                            }
                            move = self.env['account.move'].create(move_vals)
                            # We leave it as DRAFT for review
                            svl.write({'account_move_id': move.id})
            except Exception as e:
                _logger.error("Auto Cleanup failed for %s: %s", product.name, str(e))
                continue
