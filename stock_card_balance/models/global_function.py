from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, time, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict
from itertools import groupby

class DtiGlobalFunctionStockReport(models.TransientModel):
    _name = 'dti.global.function.stock.report'

    def _get_stock_card(self, company_id, start_date, end_date, location_id, products):
        DATA_REPORT = []

        location_obj = self.env['stock.location']

        def _is_in(move):
            return move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal'
        
        def _is_out(move):
            return move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal'
        
        def _is_internal(move):
            return move.location_id.usage == 'internal' and move.location_dest_id.usage == 'internal'

        tmp_start_date = datetime.strptime(str(start_date) + ' 00:00:00','%Y-%m-%d %H:%M:%S')
        tmp_end_date = datetime.strptime(str(end_date) + ' 23:59:59','%Y-%m-%d %H:%M:%S')

        product_ids = False
        if location_id:
            location_id = list(set(location_id))
        if products:
            
            product_ids = self.env['product.product'].with_context(location=location_id,to_date=tmp_start_date).browse(products)
        else:
            
            product_ids = self.env['product.product'].with_context(location=location_id, to_date=tmp_start_date).search([
                '|',('company_id', '=', False),
                ('company_id', '=', company_id),
                ('type', 'in', ('product', 'consu')),
            ])
        


        domain_valuation_layers = [('product_id', 'in', product_ids.ids), ('date', '>', tmp_start_date),
                                   ('date', '<=', tmp_end_date),
                                   ('state', '=', 'done')
                                   ]
        
        if location_id:
            location_obj = self.env['stock.location'].browse(location_id)
            location_obj |= self.env['stock.location'].search([('location_id', 'child_of', location_obj.ids)])
            domain_valuation_layers += ['|',('location_id', 'in', location_obj.ids),
                                        ('location_dest_id', 'in', location_obj.ids)]
            

        stock_valuation_layers = self.env['stock.move'].search(domain_valuation_layers, order='date')

        valuation_by_product = defaultdict(lambda: self.env['stock.move'])
        
        for product_id, layers in groupby(stock_valuation_layers, key=lambda x: x.product_id.id):
            valuation_by_product[product_id] |= self.env['stock.move'].concat(*layers)
        
        for product in product_ids:

            DATA_REPORT_LINE = []
            seq = 1
            
            move_ids = valuation_by_product.get(product.id, self.env['stock.move'])

            beginning_qty = product.qty_available
            DATA_REPORT_LINE.append({
                'seq'               : seq,
                'date'              : tmp_start_date.strftime("%Y-%m-%d %H:%M:%S"),
                'operation'         : 'Beginning Balance',
                'reference'         : '-',
                'move_in'           : beginning_qty if beginning_qty > 0 else 0,
                'move_out'          : beginning_qty if beginning_qty < 0 else 0,
                'total_value'       : product.total_value,
                'balance_value'     : product.total_value,
                'balance_qty'       : beginning_qty,
            })
            seq += 1

            balance_qty = beginning_qty
            balance_value = product.total_value
            is_mutation = False
            for move in move_ids:
                move = move.sudo()
                quantity = move.quantity
                if _is_out(move):
                    quantity = -quantity

                elif _is_internal(move):
                    if location_obj:
                        if move.location_id in location_obj and move.location_dest_id not in location_obj:
                            quantity = -quantity
                        elif move.location_id not in location_obj and move.location_dest_id in location_obj:
                            quantity = quantity
                        else:
                            continue
                    else:
                        continue

                balance_qty += quantity
                is_mutation = True
                move_value = sum(move.stock_valuation_layer_ids.mapped('value'))
                balance_value += move_value

                DATA_REPORT_LINE.append({
                    'seq'               : seq,
                    'date'              : move.date.strftime("%Y-%m-%d %H:%M:%S"),
                    'operation'         : move.reference,
                    'reference'         : move.origin,
                    'move_in'           : move.quantity if quantity > 0 else 0,
                    'move_out'          : move.quantity if quantity < 0 else 0,
                    'balance_qty'       : balance_qty,
                    'balance_value'    : balance_value,
                    'total_value'       : move_value,
                })

                seq += 1

            if beginning_qty > 0 or is_mutation:
                DATA_REPORT.append({
                    'seq'               : seq,
                    'code'              : product.default_code,
                    'product'           : product.with_context(display_default_code=False).display_name,
                    'uom'               : product.uom_id.name,
                    'data_ids'          : DATA_REPORT_LINE,
                    'ending_balance'    : balance_qty,
                    'ending_value'       : balance_value,
                })

        return DATA_REPORT

    def _get_stock_balance(self, company_id, start_date, end_date, location_id, products):
        DATA_REPORT = []

        tmp_start_date = datetime.strptime(str(start_date) + ' 00:00:00','%Y-%m-%d %H:%M:%S')
        tmp_end_date = datetime.strptime(str(end_date) + ' 23:59:59','%Y-%m-%d %H:%M:%S')

        product_ids = False
        if products:
            self._cr.execute(
                """ SELECT pp.id
                        FROM product_product AS pp
                            INNER JOIN product_template pt ON pt.id=pp.product_tmpl_id
                    WHERE
                        pp.id IN %s
                """, (products, ))
            product_ids = self.env['product.product'].browse([r[0] for r in self._cr.fetchall()])
        else:
            self._cr.execute(
                """ SELECT pp.id
                        FROM product_product AS pp
                            INNER JOIN product_template pt ON pt.id=pp.product_tmpl_id
                    WHERE
                        (pt.company_id=%s OR pt.company_id IS NULL) AND pt.type IN ('product','consu') AND pp.active=True
                """, (company_id, ))
            product_ids = self.env['product.product'].browse([r[0] for r in self._cr.fetchall()])

        seq = 1
        for product in product_ids:
            beginning_qty = 0
            in_product_qty = 0
            out_product_qty = 0

            self._cr.execute(
                """ SELECT sm.id
                        FROM stock_move AS sm
                    WHERE
                        (sm.location_id=%s OR sm.location_dest_id=%s) AND sm.product_id=%s AND sm.date<=%s AND sm.state='done'
                """, (location_id, location_id, product.id, tmp_end_date.strftime("%Y-%m-%d %H:%M:%S"), ))
            move_ids = self.env['stock.move'].browse([r[0] for r in self._cr.fetchall()])
            for move in move_ids:
                if move.date < tmp_start_date:
                    if move.location_id.id == location_id:
                        beginning_qty -= move.product_uom_qty
                    elif move.location_dest_id.id == location_id:
                        beginning_qty += move.product_uom_qty
                else:
                    if move.location_id.id == location_id:
                        out_product_qty += move.product_uom_qty
                    elif move.location_dest_id.id == location_id:
                        in_product_qty += move.product_uom_qty

            DATA_REPORT.append({
                'seq'               : seq,
                'code'              : product.default_code,
                'product'           : product.name,
                'uom'               : product.uom_id.name,
                'beginning'         : beginning_qty,
                'in_qty'            : in_product_qty,
                'out_qty'           : out_product_qty,
                'ending'            : beginning_qty + in_product_qty - out_product_qty,
            })
            seq += 1

        return DATA_REPORT


