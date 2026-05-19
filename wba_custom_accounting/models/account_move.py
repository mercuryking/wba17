from odoo import fields, api, models, _
from num2words import num2words

class AccountMove(models.Model):
    _inherit = 'account.move'

    keterangan_text = fields.Text(string='Keterangan')
    disetujui_oleh = fields.Many2one('res.partner', string='Signed By')
    last_payment_date = fields.Date(string='Last Payment Date', compute='_compute_last_payment_date', store=True)
    discount_global_percentage = fields.Float(string='Discount Global (%)', default=0.0)
    discount_global_amount = fields.Monetary(string='Discount Global', compute='_compute_discount_global_amount', store=True)
    base_untaxed_amount = fields.Monetary(string='Base Untaxed', compute='_compute_base_amount', store=True)
    base_tax_amount = fields.Monetary(string='Base Tax', compute='_compute_base_amount', store=True)
    base_total = fields.Monetary(string='Base Total', compute='_compute_base_amount', store=True)
    amount_total = fields.Monetary(precompute=True)
    paid = fields.Monetary(string='paid', compute='_compute_paid', store=True)
    amount_total_before_discount_tax = fields.Monetary(String="Total Before Discount Tax", compute='_compute_amount_total_before_discount_tax', store=True, readonly=True)
    no_invoice = fields.Char(string='No. Invoice')
    picking_ids = fields.Many2many('stock.picking', string='Delivery Orders', compute='_compute_picking_ids', store=True, readonly=False)
    available_picking_ids = fields.Many2many('stock.picking', string='Available Delivery Orders', compute='_compute_available_picking_ids')

    @api.depends('move_type', 'line_ids.amount_residual')
    def _compute_last_payment_date(self):
        for move in self:
            date = False
            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                payment_date = []
                reconciled_partials = move.sudo()._get_all_reconciled_invoice_partials()
                reconciled_partials = move.sudo()._get_all_reconciled_invoice_partials()
                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial['aml']
                    payment_date.append(counterpart_line.date)
                if payment_date:
                    date = max(payment_date)
            move.last_payment_date = date

    @api.depends('invoice_line_ids.total_before_discount_tax')
    def _compute_amount_total_before_discount_tax(self):
        for move in self:
            total = sum(move.invoice_line_ids.mapped('total_before_discount_tax'))
            move.amount_total_before_discount_tax = total

    @api.depends('amount_total_signed', 'amount_residual_signed')
    def _compute_paid(self):
        for move in self:
            move.paid = move.amount_total_signed - move.amount_residual_signed
    

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'discount_global_percentage')
    def _compute_base_amount(self):
        for move in self:
            move.base_untaxed_amount = move.amount_untaxed / (1 - (move.discount_global_percentage / 100.0))
            move.base_tax_amount = move.amount_tax / (1 - (move.discount_global_percentage / 100.0))
            move.base_total = move.amount_total / (1 - (move.discount_global_percentage / 100.0))

    
   
    @api.depends('base_total', 'discount_global_percentage')
    def _compute_discount_global_amount(self):
        for move in self:
            move.discount_global_amount = move.base_total * (move.discount_global_percentage / 100.0)

    @api.depends('discount_global_percentage')
    def _compute_tax_totals(self):
        super(AccountMove, self)._compute_tax_totals()
        for move in self.filtered(lambda m: m.tax_totals):
            tax_totals = move.tax_totals
            base_total = tax_totals.get('amount_total') / (1 - (move.discount_global_percentage / 100.0))
            discount_amount = tax_totals.get('amount_total') - base_total

    def _num_2_words(self, amount):
        words = num2words(amount, lang='id').title()
        if words.endswith(' Koma Nol'):
            words = words.replace(' Koma Nol', '')
        return words
    
    def count_decimal_places(self,number):
        number_str = f"{number:.10f}".rstrip('0')
        if '.' in number_str:
            decimal_places = len(number_str.split('.')[1])
        else:
            decimal_places = 0
        return min(decimal_places,2)


    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        super(AccountMove, self)._compute_suitable_journal_ids()
        for m in self.filtered(lambda m: not m.invoice_filter_type_domain):
            company = m.company_id or self.env.company
            m.suitable_journal_ids = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
            ])


    
    def remove_move_reconcile(self):
        """ Undo a reconciliation """
        if self._context.get('dont_remove_reconcile_payment', False):
            self = self.filtered(lambda line: line.account_id.account_type not in ('asset_receivable', 'liability_payable'))
            if not self:
                return
        return super(AccountMoveLine, self).remove_move_reconcile()
    

    @api.depends('invoice_line_ids.sale_line_ids', 'invoice_line_ids.sale_line_ids.move_ids', 'invoice_line_ids.sale_line_ids.move_ids.state')
    def _compute_picking_ids(self):
        for move in self:
            picking_ids = self.env['stock.picking']
            
            for line in move.invoice_line_ids:
                for sale_line in line.sale_line_ids:
                    move_ids = sale_line.move_ids.filtered(lambda m: m.state != 'cancel')
                    if len(move_ids) == 1:
                        picking_ids |= move_ids.picking_id
                    elif len(move_ids) > 1:
                        match_picking = self.env['stock.picking']
                        for sm in move_ids:
                            if sm.quantity == line.quantity:
                                match_picking |= sm.picking_id
                        picking_ids |= match_picking
            move.picking_ids = picking_ids

    @api.depends('invoice_line_ids')
    def _compute_available_picking_ids(self):
        for move in self:
            move.available_picking_ids = move.invoice_line_ids.sale_line_ids.move_ids.picking_id


            
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    total_before_discount_tax = fields.Monetary(String="Total Before Discount Tax", 
                                                compute='_compute_total_before_discount_tax',
                                                currency_field='currency_id', store=True, readonly=True)
    
    @api.depends('price_unit', 'quantity')
    def _compute_total_before_discount_tax(self):
        for line in self:
            line.total_before_discount_tax = line.price_unit * line.quantity