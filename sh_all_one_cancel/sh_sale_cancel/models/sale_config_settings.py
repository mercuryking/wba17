# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    operation_type = fields.Selection([('cancel', 'Cancel Only'), ('cancel_draft', 'Cancel and Reset to Draft'), ('cancel_delete', 'Cancel and Delete')],
                                      default='cancel', string=" Opration Type")

    cancel_delivery = fields.Boolean("Cancel Delivery Order")
    cancel_invoice = fields.Boolean("Cancel Invoice and Payment")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    operation_type = fields.Selection(
                                       string=" Opration Type", related="company_id.operation_type", readonly=False)

    cancel_delivery = fields.Boolean(
        "Cancel Delivery Order", related='company_id.cancel_delivery', readonly=False)
    cancel_invoice = fields.Boolean(
        "Cancel Invoice and Payment", related='company_id.cancel_invoice', readonly=False)
