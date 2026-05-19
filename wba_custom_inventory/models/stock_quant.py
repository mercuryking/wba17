from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.constrains('quantity')
    def _check_negative_quantity(self):
        for quant in self:
            if quant.location_id.usage == 'internal' and quant.quantity < 0:
                raise UserError(_('Negative quantity is not allowed, please check the stock %s in location %s.') % (quant.product_id.name, quant.location_id.name))
            
        