from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError, ValidationError
from odoo.tools import formatLang
import re
from odoo.addons.purchase.models.purchase_order import PurchaseOrder as PurchaseOrderBase

_logger = logging.getLogger(__name__)




@api.model_create_multi
def create(self, vals_list):
    orders = self.browse()
    partner_vals_list = []
    for vals in vals_list:
        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        # Ensures default picking type and currency are taken from the right company.
        self_comp = self.with_company(company_id)
        if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                category_id = vals.get('category_id')
                category_obj = self.env['purchase.order.category'].browse(category_id) if category_id else None
                vals['name'] = category_obj.sequence_id.next_by_id(sequence_date=seq_date) 
        vals, partner_vals = self._write_partner_values(vals)
        partner_vals_list.append(partner_vals)
        orders |= super(PurchaseOrderBase, self_comp).create(vals)
    for order, partner_vals in zip(orders, partner_vals_list):
        if partner_vals:
            order.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
    return orders


PurchaseOrderBase.create = create

class PurchaseOrder(models.Model):
    _inherit = ["purchase.order", "sequence.mixin"]
    _name = "purchase.order"
    _sequence_index = 'category_id'
    _sequence_date_field = 'create_date'


    discount_global_type = fields.Selection(
        selection=[
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed Amount'),
        ],
        string='Discount Global Type',
        copy=False,
    )
    discount_global_percentage = fields.Float(string='Discount Global (%)', default=0.0, copy=False)
    discount_global_fixed_amount = fields.Monetary(string='Discount Global Fixed Amount', default=0.0, copy=False)
    amount_total_before_discount_global = fields.Monetary(string='Total Before Discount Global', compute='_compute_amount_total_before_discount_global')
    discount_global_amount = fields.Monetary(string='Discount Global Amount', compute='_compute_amount_total_before_discount_global')

    disetujui_oleh = fields.Char(string='Disetujui Oleh')
    category_id = fields.Many2one(comodel_name='purchase.order.category', string='Category')

    carrier_id = fields.Many2one('delivery.carrier', string='Delivery Method')
    delivery_set = fields.Boolean(compute='_compute_delivery_state', store=False)
    recompute_delivery_price = fields.Boolean(string='Delivery cost should be recomputed')

    @api.depends('category_id')
    def _compute_name(self):
        for order in self:
            print("order.state------------------------------", order.state)
            if order.state in ['draft', 'sent'] :
                order._set_next_sequence()

    def _get_starting_sequence(self, category_id=None):
        category_id = category_id or self.category_id
        return "%s/0000" % (category_id.seqeunce_code if category_id else "GENERAL")


    def _get_last_sequence_domain(self, relaxed=False):
        #pylint: disable=sql-injection
        # EXTENDS account sequence.mixin
        self.ensure_one()
        if  not self.category_id:
            return "WHERE FALSE", {}
        where_string = "WHERE category_id = %(category_id)s AND name != '/'"    
        param = {'category_id': self.category_id.id}

        if not relaxed:
            domain = [('category_id', '=', self.category_id.id), ('id', '!=', self.id or self._origin.id), ('name', 'not in', ('/', '', False))]
            
            reference_po_name = self.sudo().search(domain + [('create_date', '<=', self.create_date)], order='create_date desc', limit=1).name
            if not reference_po_name:
                reference_po_name = self.sudo().search(domain, order='create_date asc', limit=1).name
            sequence_number_reset = self._deduce_sequence_number_reset(reference_po_name)
            date_start, date_end = self._get_sequence_date_range(sequence_number_reset)
            where_string += """ AND create_date BETWEEN %(date_start)s AND %(date_end)s"""
            param['date_start'] = date_start
            param['date_end'] = date_end
            if sequence_number_reset in ('year', 'year_range'):
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_monthly_regex.split('(?P<seq>')[0]) + '$'
            elif sequence_number_reset == 'never':
                param['anti_regex'] = re.sub(r"\?P<\w+>", "?:", self._sequence_yearly_regex.split('(?P<seq>')[0]) + '$'

            if param.get('anti_regex'):
                where_string += " AND sequence_prefix !~ %(anti_regex)s "

        return where_string, param
    

    @api.depends('amount_total', 'discount_global_percentage')
    def _compute_amount_total_before_discount_global(self):
        for order in self:
            order.amount_total_before_discount_global = order.amount_total / (1 - (order.discount_global_percentage / 100.0))
            order.discount_global_amount = order.amount_total - order.amount_total_before_discount_global



    def action_open_discount_wizard(self):
            self.ensure_one()
            return {
                'name': _("Discount"),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order.discount',
                'view_mode': 'form',
                'target': 'new',
            }   
    
    def _compute_delivery_state(self):
        for order in self:
            order.delivery_set = any(line.is_delivery for line in order.order_line)

    def action_open_delivery_wizard(self):
        self.ensure_one()
        view_id = self.env.ref(
            'wba_custom_purchase.choose_delivery_carrier_purchase_view_form'
        ).id
        if self.env.context.get('carrier_recompute'):
            name = _('Update shipping cost')
            carrier = self.carrier_id
        else:
            name = _('Add a shipping method')
            carrier = self.env['delivery.carrier']
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'choose.delivery.carrier.purchase',
            'view_id': view_id,
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_carrier_id': carrier.id if carrier else False,
            }
        }

    def _remove_delivery_line(self):
        delivery_lines = self.order_line.filtered('is_delivery')
        if not delivery_lines:
            return
        to_delete = delivery_lines.filtered(lambda x: x.qty_invoiced == 0)
        if not to_delete:
            raise UserError(
                _('You cannot update the shipping costs on a purchase order '
                  'where it has already been invoiced!')
            )
        to_delete.unlink()

    def set_delivery_line(self, carrier, amount):
        self._remove_delivery_line()
        for order in self:
            order._create_delivery_line(carrier, amount)
        return True

    def _prepare_delivery_line_vals(self, carrier, price_unit):
        # Apply fiscal position on taxes
        taxes = carrier.product_id.supplier_taxes_id._filter_taxes_by_company(self.company_id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        if carrier.product_id.description_pickingin:
            po_description = '%s: %s' % (carrier.name, carrier.product_id.description_pickingin)
        else:
            po_description = carrier.name

        values = {
            'order_id': self.id,
            'name': po_description,
            'price_unit': price_unit,
            'product_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'taxes_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        return values

    def _create_delivery_line(self, carrier, price_unit):
        values = self._prepare_delivery_line_vals(carrier, price_unit)
        return self.env['purchase.order.line'].sudo().create(values)


    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res['discount_global_percentage'] = self.discount_global_percentage
        res['discount_global_amount'] = self.discount_global_fixed_amount
        # res['discount_global_type'] = self.discount_global_type
        return res
    


    def _recompute_discount_fixed_amount(self):
        for order in self:
            order_line_with_tax = order.order_line.filtered(lambda line: line.taxes_id)
            order_line_without_tax = order.order_line - order_line_with_tax
            
            if order_line_with_tax and order_line_without_tax:
                raise UserError(_("You cannot apply a fixed discount when some order lines have taxes."))
            
            if len(order_line_with_tax.taxes_id) > 1:
                raise UserError(_("You cannot apply a fixed discount when some order lines have multiple taxes."))
            
            order.write({
                'discount_global_percentage' : order.discount_global_fixed_amount / order.amount_total_before_discount_global * 100.0,
            })


    
    
class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_delivery = fields.Boolean(string='Is a Delivery', default=False)

    price_subtotal_without_discount_global = fields.Monetary(string='Subtotal Without Discount Global', compute='_compute_amount_without_discount_global', store=True)
    price_total_without_discount_global = fields.Monetary(string='Total Without Discount Global', compute='_compute_amount_without_discount_global', store=True)
    
    @api.depends('price_subtotal', 'price_total', 'order_id.discount_global_percentage')
    def _compute_amount_without_discount_global(self):
        for line in self:
            base_subtotal = line.price_subtotal / (1 - (line.order_id.discount_global_percentage / 100.0))
            base_total = line.price_total / (1 - (line.order_id.discount_global_percentage / 100.0))
            line.price_subtotal_without_discount_global = base_subtotal
            line.price_total_without_discount_global = base_total


    @api.depends("order_id.discount_global_percentage")
    def _compute_amount(self):
        super(PurchaseOrderLine, self)._compute_amount()


    
    def _convert_to_tax_base_line_dict(self):
        res = super(PurchaseOrderLine, self)._convert_to_tax_base_line_dict()
        if self.order_id.discount_global_percentage:
            res['discount'] = res['discount'] + self.order_id.discount_global_percentage - (res['discount'] * self.order_id.discount_global_percentage / 100.0)
        return res


    def _get_gross_price_unit(self):
        price_unit = super(PurchaseOrderLine, self)._get_gross_price_unit()
        if self.order_id.discount_global_percentage:
            price_unit = price_unit - (price_unit * self.order_id.discount_global_percentage / 100.0)
        
        
        return price_unit
    


    @api.model_create_multi
    def create(self, vals_list):
        order_lines = super(PurchaseOrderLine, self).create(vals_list)
        for po in order_lines.order_id.filtered(lambda po: po.discount_global_type == 'fixed'):
            po.with_context(tracking_disable=True)._recompute_discount_fixed_amount()

        return order_lines


    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if 'product_qty' in vals or 'price_unit' in vals or 'discount' in vals or 'taxes_id' in vals:
            for po in self.order_id.filtered(lambda po: po.discount_global_type == 'fixed'):
                po.with_context(tracking_disable=True)._recompute_discount_fixed_amount()
        return res
    



    