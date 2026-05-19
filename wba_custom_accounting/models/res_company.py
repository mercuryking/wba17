from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    shipping_product_id = fields.Many2one(
        'product.product',
        string='Shipping Product',
        help="Product used for shipping charges in sales orders.",
        domain=[('type', '=', 'service')]
    )