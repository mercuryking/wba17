from odoo import models, fields, api, _

class SaleOrderCategory(models.Model):
    _name = "sale.order.category"
    _description = "Sale Order Category"

    name = fields.Char(string="Category Name", required=True)
    sequence_code = fields.Char(string="Sequence Prefix", required=True)
    sequence_id = fields.Many2one('ir.sequence', string='Sequence', copy=False, readonly=True)


    @api.model
    def create(self, vals):
        category = super(SaleOrderCategory, self).create(vals)
        sequence_vals = {
            'name': _('Sales Order %s') % (category.name),
            'code': 'sale.order.category.%s' % (category.id),
            'prefix': category.sequence_code,
            'padding': 4,
        }
        sequence = self.env['ir.sequence'].create(sequence_vals)
        category.sequence_id = sequence.id
        return category

    def unlink(self):
        for category in self:
            if category.sequence_id:
                category.sequence_id.unlink()
        return super(SaleOrderCategory, self).unlink()

    def write(self, vals):
        res = super(SaleOrderCategory, self).write(vals)
        for category in self:
            if 'sequence_code' in vals and category.sequence_id:
                category.sequence_id.prefix = category.sequence_code
            elif 'sequence_code' in vals and not category.sequence_id:
                sequence_vals = {
                    'name': _('Sales Order %s') % (category.name),
                    'code': 'sale.order.category.%s' % (category.id),
                    'prefix': category.sequence_code,
                    'padding': 4,
                }
                sequence = self.env['ir.sequence'].create(sequence_vals)
                category.sequence_id = sequence.id
        return res