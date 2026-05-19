from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    shipping_product_id = fields.Many2one('product.product', string='Shipping Product', related='company_id.shipping_product_id', readonly=False)