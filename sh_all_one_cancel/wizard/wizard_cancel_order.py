from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ast import literal_eval


class WizardCancelOrder(models.TransientModel):
    _name = 'wizard.cancel.order'

    reason = fields.Text('Reason', required=True)
    model = fields.Char('Model', required=True)
    res_id = fields.Char('Res ID', required=True)
    action_name = fields.Char('Action Name')

    def action_cancel_order(self):
        res_ids = literal_eval(self.res_id)
        record = self.env[self.model].browse(res_ids)
        if hasattr(record, self.action_name):
            action_method = getattr(record.with_context(cancel_reason=self.reason), self.action_name)
            if callable(action_method):
                action_method()
            else:
                raise UserError(_('The action "%s" is not callable on model "%s".') % (self.action_name, self.model))
        else:
            raise UserError(_('The action "%s" does not exist on model "%s".') % (self.action_name, self.model))

   