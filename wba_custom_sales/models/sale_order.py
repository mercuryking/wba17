from odoo import models, fields, api, _
from num2words import num2words
from odoo.exceptions import UserError
import re
from odoo.addons.sale.models.sale_order import SaleOrder as SaleOrderBase



@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _("New")) == _("New"):
            seq_date = fields.Datetime.context_timestamp(
                self, fields.Datetime.to_datetime(vals['date_order'])
            ) if 'date_order' in vals else None

            category_id = vals.get('category_id')
            category_obj = self.env['sale.order.category'].browse(category_id) if category_id else None
            if category_obj and category_obj.sequence_id:
                vals['name'] = category_obj.sequence_id.next_by_id(sequence_date=seq_date)
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.order', sequence_date=seq_date) or _("New")

    return super(SaleOrderBase, self).create(vals_list)


SaleOrderBase.create = create



class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'sequence.mixin']
    _sequence_index = 'category_id'
    _sequence_date_field = 'create_date'

    keterangan_text = fields.Text(string='Keterangan')
    disetujui_oleh = fields.Many2one('res.partner', string='Signed By')
    category_id = fields.Many2one('sale.order.category', string='Category')



    @api.depends('category_id', 'create_date', 'state')
    def _compute_name(self):
        for order in self:
            if order.state in ['draft', 'sent']:
                order._set_next_sequence()

    
    def _get_starting_sequence(self):
        self.ensure_one()

        return "%s/0000" % (self.category_id.sequence_code if self.category_id else "GENERAL")
    

    def _get_last_sequence_domain(self, relaxed=False):
        # EXTENDS account.sequence.mixin
        self.ensure_one()

        if not self.category_id:
            return "WHERE FALSE", {}

        where_string = "WHERE category_id = %(category_id)s AND name != '/'"
        param = {'category_id': self.category_id.id}

        if relaxed or not self.create_date:
            return where_string, param

        domain = [
            ('category_id', '=', self.category_id.id),
            ('id', '!=', self.id or self._origin.id),
            ('name', 'not in', ('/', '', False)),
        ]

        reference = self.sudo().search(
            domain + [('create_date', '<=', self.create_date)],
            order='create_date desc',
            limit=1
        )

        if not reference:
            reference = self.sudo().search(domain, order='create_date asc', limit=1)

        if not reference:
            return where_string, param

        sequence_number_reset = self._deduce_sequence_number_reset(reference.name)
        date_start, date_end = self._get_sequence_date_range(sequence_number_reset)

        where_string += " AND create_date BETWEEN %(date_start)s AND %(date_end)s"
        param.update({
            'date_start': date_start,
            'date_end': date_end,
        })

        if sequence_number_reset in ('year', 'year_range'):
            param['anti_regex'] = re.sub(
                r"\?P<\w+>", "?:",
                self._sequence_monthly_regex.split('(?P<seq>')[0]
            ) + '$'
        elif sequence_number_reset == 'never':
            param['anti_regex'] = re.sub(
                r"\?P<\w+>", "?:",
                self._sequence_yearly_regex.split('(?P<seq>')[0]
            ) + '$'

        if param.get('anti_regex'):
            where_string += " AND sequence_prefix !~ %(anti_regex)s"

        return where_string, param


    def _num_2_words(self, amount):
        words = num2words(amount, lang='id').title()
        if words.endswith(' Koma Nol'):
            words = words.replace(' Koma Nol', '')
        return words