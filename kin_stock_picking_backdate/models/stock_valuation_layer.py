from datetime import datetime
from psycopg2.extensions import AsIs

from odoo import models, api, fields, _

from odoo.exceptions import UserError


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model_create_multi
    def create(self, vals_list):
        # do actual processing
        records = super(StockValuationLayer, self).create(vals_list)

        # force create_date and write_date with context's manual_validate_date_time
        manual_validate_date_time = self._context.get('manual_validate_date_time', False)
        if manual_validate_date_time:
            if isinstance(manual_validate_date_time, datetime):
                manual_validate_date_time = fields.Datetime.to_string(manual_validate_date_time)

            # we use SQL to write create_date and write_date
            # since Odoo does not allow changing those using its API
            if records:
                for svl in records:
                    self.env.cr.execute("""
                        UPDATE %s
                        SET create_date=%s
                        WHERE id = %s
                        """, (
                        AsIs(self._table),
                        manual_validate_date_time,
                        svl.id
                        )
                    )
                        
        return records

