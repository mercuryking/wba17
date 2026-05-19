from odoo import models, api, fields, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _set_backdate(self, backdate):
        """
        set backdate for done stock moves and their conresponding done stock move lines
        """
        stock_moves = self.filtered(lambda x: x.state == 'done')
        for move in stock_moves:
            move.write({'date': backdate})

        move_line_ids = self.mapped('move_line_ids').filtered(lambda x: x.state == 'done')
        if move_line_ids:
            move_line_ids.write({'date': backdate})


    def _action_done(self, cancel_backorder=False):
        # do actual processing
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        # overwrite date field where applicable
        manual_validate_date_time = self._context.get('manual_validate_date_time', False)
        if manual_validate_date_time:
            self._set_backdate(manual_validate_date_time)
        return res
