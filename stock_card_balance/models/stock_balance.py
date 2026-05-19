from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, time, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import base64
from io import BytesIO
import xlsxwriter
import calendar
import collections

class WizardDtiStockBalanceReport(models.TransientModel):
    _name = 'wizard.dti.stock.balance.report'

    @api.model
    def _default_company_id(self):
        return self.env.user.company_id.id

    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=_default_company_id)
    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    location_id = fields.Many2one(comodel_name="stock.location", string="Location", required=True)
    product_ids = fields.Many2many(comodel_name="product.product", string="Products")
    file = fields.Binary(string='File')

    @api.onchange("location_id","company_id")
    def onchange_location_id(self):
        ids_location = []
        domain = {}
        
        location_ids = self.env['stock.location'].sudo().search([('usage','=','internal'),('company_id','=', self.company_id.id)])
        for location in location_ids:
            ids_location.append(location.id)

        domain['location_id'] = [('id','in', ids_location)]
        return {'domain':domain}

    def button_print_excel(self):
        self.ensure_one()

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
        #################################################################################
        left_title = workbook.add_format({'bold': 1, 'valign':'vcenter', 'align':'left'})
        left_title.set_font_size('15')
        left_title_sub = workbook.add_format({'valign':'vcenter', 'align':'left'})
        left_title_sub.set_font_size('12')
        center_title_sub = workbook.add_format({'valign':'vcenter', 'align':'center'})
        center_title_sub.set_font_size('12')
        header_title = workbook.add_format({'bold': 1, 'valign':'vcenter', 'align':'left'})
        header_title.set_font_size('12')
        #################################################################################
        header_table = workbook.add_format({'valign':'vcenter', 'align':'center', 'font_color':'#FFFFFF'})
        header_table.set_font_size('12')
        header_table.set_bg_color('#02569C')
        header_table.set_border()
        #################################################################################
        center_table = workbook.add_format({'valign':'vcenter', 'align':'center'})
        center_table.set_font_size('11')
        center_table.set_border()
        #################################################################################
        left_table = workbook.add_format({'valign':'vcenter', 'align':'left'})
        left_table.set_font_size('11')
        left_table.set_border()
        #################################################################################
        numb_table = workbook.add_format({'valign':'vcenter', 'align':'right','num_format':'#,##0.00'})
        numb_table.set_font_size('11')
        numb_table.set_border()
        #################################################################################
        left_footer = workbook.add_format({'bold': 1, 'valign':'vcenter', 'align':'left'})
        left_footer.set_font_size('12')
        left_footer.set_border()
        #################################################################################
        numb_footer = workbook.add_format({'bold': 1, 'valign':'vcenter', 'align':'right','num_format':'#,##0.00'})
        numb_footer.set_font_size('12')
        numb_footer.set_border()

        worksheet1 = workbook.add_worksheet("All")
        worksheet1.set_column('A:A', 5)
        worksheet1.set_column('B:B', 15)
        worksheet1.set_column('C:C', 2)
        worksheet1.set_column('D:D', 30)
        worksheet1.set_column('E:E', 20)
        worksheet1.set_column('F:F', 20)
        worksheet1.set_column('G:G', 2)
        worksheet1.set_column('H:H', 20)
        worksheet1.set_column('I:I', 20)
        worksheet1.set_column('J:J', 20)

        today = (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        filename = str(self.company_id.name) + " - Stock Balance Report"
        data_report = self.env['dti.global.function.stock.report']._get_stock_balance(self.company_id.id, self.start_date, self.end_date, self.location_id.id, self.product_ids.ids)

        worksheet1.merge_range('A1:J1', 'STOCK BALANCE REPORT', left_title)
        worksheet1.merge_range('A2:J2', str(self.location_id.company_id.name), left_title_sub)
        
        i = 3
        worksheet1.merge_range(i, 0, i, 1, 'Period', left_title_sub)
        worksheet1.write(i, 2, ':', center_title_sub)
        worksheet1.write(i, 3, datetime.strptime(str(self.start_date), "%Y-%m-%d").strftime("%d/%m/%Y") + ' to ' + \
                datetime.strptime(str(self.end_date), "%Y-%m-%d").strftime("%d/%m/%Y"), left_title_sub)
        worksheet1.write(i, 5, 'Total Item', left_title_sub)
        worksheet1.write(i, 6, ':', center_title_sub)
        worksheet1.write(i, 7, str(len(data_report)) + ' item', left_title_sub)
        i += 1
        worksheet1.merge_range(i, 0, i, 1, 'Location', left_title_sub)
        worksheet1.write(i, 2, ':', center_title_sub)
        worksheet1.write(i, 3, self.location_id.display_name, left_title_sub)
        worksheet1.write(i, 5, 'Printed on', left_title_sub)
        worksheet1.write(i, 6, ':', center_title_sub)
        worksheet1.write(i, 7, datetime.strptime(today, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S") + ' by ' + self.env.user.name, left_title_sub)
        i += 2
        worksheet1.merge_range(i, 0, i+1, 0, 'No', header_table)
        worksheet1.merge_range(i, 1, i+1, 2, 'Product Code', header_table)
        worksheet1.merge_range(i, 3, i+1, 3, 'Product Name', header_table)
        worksheet1.merge_range(i, 4, i+1, 4, 'UoM', header_table)
        worksheet1.merge_range(i, 5, i+1, 6, 'Beginning Balance', header_table)
        worksheet1.merge_range(i, 7, i, 8, 'Mutation', header_table)
        worksheet1.write(i+1, 8, 'In', header_table)
        worksheet1.write(i+1, 7, 'Out', header_table)
        worksheet1.merge_range(i, 9, i+1, 9, 'Ending Balance', header_table)
        i += 2

        for data in data_report:
            worksheet1.write(i, 0, data['seq'], center_table)
            worksheet1.merge_range(i, 1, i, 2, data['code'], left_table)
            worksheet1.write(i, 3, data['product'], left_table)
            worksheet1.write(i, 4, data['uom'], center_table)
            worksheet1.merge_range(i, 5, i, 6, data['beginning'], numb_table)
            worksheet1.write(i, 8, data['in_qty'], numb_table)
            worksheet1.write(i, 7, data['out_qty'], numb_table)
            worksheet1.write(i, 9, data['ending'], numb_table)
            i += 1

        workbook.close()
        file=base64.encodebytes(fp.getvalue())
        self.write({'file':file})
        fp.close()
        
        return{
            'type' : 'ir.actions.act_url',
            'url': 'web/content/?model=wizard.dti.stock.balance.report&field=file&download=true&id=%s&filename=%s.xlsx'%(self.id,filename),
            'target': 'new',
        }


