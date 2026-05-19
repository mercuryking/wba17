from odoo import models, fields, api, _
from odoo.tools import float_is_zero

class AccountMove(models.Model):
    _inherit = 'account.move'


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_gross_unit_price(self):
        if float_is_zero(self.quantity, precision_rounding=self.product_uom_id.rounding):
            return self.price_unit

        price_unit = self.price_subtotal / self.quantity

       
        
        return -price_unit if self.move_id.move_type == 'in_refund' else price_unit