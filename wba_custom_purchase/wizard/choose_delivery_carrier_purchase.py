from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ChooseDeliveryCarrierPurchase(models.TransientModel):
    _name = 'choose.delivery.carrier.purchase'
    _description = 'Delivery Carrier Selection Wizard (Purchase)'

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    order_id = fields.Many2one('purchase.order', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='order_id.partner_id')
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Shipping Method',
        required=True,
    )
    delivery_type = fields.Selection(related='carrier_id.delivery_type')
    delivery_price = fields.Float()
    display_price = fields.Float(string='Cost', readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    company_id = fields.Many2one('res.company', related='order_id.company_id')
    available_carrier_ids = fields.Many2many(
        'delivery.carrier',
        compute='_compute_available_carrier',
        string='Available Carriers',
    )
    delivery_message = fields.Text(readonly=True)
    total_weight = fields.Float(string='Total Order Weight', readonly=False)
    weight_uom_name = fields.Char(readonly=True, default=_get_default_weight_uom)

    @api.depends('partner_id')
    def _compute_available_carrier(self):
        for rec in self:
            carriers = self.env['delivery.carrier'].search(
                self.env['delivery.carrier']._check_company_domain(rec.order_id.company_id)
            )
            rec.available_carrier_ids = carriers.available_carriers(
                rec.order_id.partner_id
            ) if rec.partner_id else carriers

    @api.onchange('carrier_id', 'total_weight')
    def _onchange_carrier_id(self):
        self.delivery_message = False
        if self.delivery_type in ('fixed', 'base_on_rule'):
            vals = self._get_shipment_rate()
            if vals.get('error_message'):
                return {'error': vals['error_message']}
        else:
            self.display_price = 0
            self.delivery_price = 0

    def _get_shipment_rate(self):
        if self.carrier_id.delivery_type == 'fixed':
            self.delivery_price = self.carrier_id.fixed_price
            self.display_price = self.carrier_id.fixed_price
            return {}
        self.display_price = 0
        self.delivery_price = 0
        return {}

    def button_confirm(self):
        self.order_id.set_delivery_line(self.carrier_id, self.delivery_price)
        self.order_id.write({
            'carrier_id': self.carrier_id.id,
            'recompute_delivery_price': False,
        })
