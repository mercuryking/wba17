from odoo import models, fields, api, _

class StockMove(models.Model):
    _inherit = 'stock.move'

    def recreate_in_svl_journal(self):
        self = self.with_context(tracking_disable=True)
        valued_move = self.sorted(key=lambda r: r.date)
        account_move_id = valued_move.stock_valuation_layer_ids.mapped('account_move_id')
        
        
        account_move_id.filtered(lambda m: m.state != 'cancel').button_cancel()
        account_move_id.sudo().unlink()
        valued_move.stock_valuation_layer_ids.sudo().unlink()
        # valued_move.product_price_update_before_done()
        # stock_valuation_layers |= valued_move._create_in_svl()
        for move in valued_move:
            svl_move = self.env['stock.valuation.layer'].sudo()
            if move._is_in():
                # AVCO: update standard_price (weighted average) sebelum buat SVL IN
                # persis seperti yg dilakukan Odoo di _action_done
                move.product_price_update_before_done()
                svl_move = move.with_context(manual_validate_date_time=move.date)._create_in_svl()
                move.product_id._run_fifo_vacuum(move.company_id)
            elif move._is_out():
                # Untuk AVCO: standard_price sudah di-update oleh product_price_update_before_done()
                # di IN move sebelumnya, jadi _create_out_svl() akan pakai harga yg benar
                svl_move = move.with_context(manual_validate_date_time=move.date)._create_out_svl()
                

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        svl_vals = super(StockMove, self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        
        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if self.env.context.get('force_period_date'):
            date = self.env.context.get('force_period_date')
        elif svl.account_move_line_id:
            date = svl.account_move_line_id.date
        else:
            date = fields.Datetime.context_timestamp(self, self.date).date()
        svl_vals.update({
            'date': date,
        })
        return svl_vals