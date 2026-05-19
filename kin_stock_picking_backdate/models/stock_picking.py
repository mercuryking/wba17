from odoo import models, api, fields, _
from datetime import date

from odoo.exceptions import UserError

def check_date(date):
    now = fields.Datetime.now()
    if date and date > now:
        raise UserError(
            _("You can not process an actual "
              "movement date in the future."))

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date_backdating = fields.Datetime(string='Actual Date')

    @api.onchange('date_backdating')
    def onchange_date_backdating(self):
        check_date(self.date_backdating)

    def _action_done(self):
        for picking in self:
            if not picking.date_backdating:
                picking.date_backdating = fields.Datetime.now()
            if picking.date_backdating:
                picking.env.context = dict(picking.env.context)
                date_backdating = picking.date_backdating
                accounting_date = date_backdating.date()
                picking.env.context.update({
                    'manual_validate_date_time': date_backdating,
                    'picking_type_code': picking.picking_type_id.code,
                    'force_period_date': accounting_date
                })
                res = super(StockPicking, picking)._action_done()

                manual_validate_date_time = picking._context.get('manual_validate_date_time', False)
                if manual_validate_date_time:
                    picking.filtered(lambda x: x.state == 'done').write({'date_done': manual_validate_date_time})

        return False