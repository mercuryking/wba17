from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, time, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import base64
from io import BytesIO
import xlsxwriter
import calendar
import collections

class WizardDtiStockCardReport(models.TransientModel):
    _name = "wizard.dti.stock.card.report"

    @api.model
    def _default_company_id(self):
        return self.env.user.company_id.id

    company_id = fields.Many2one(comodel_name="res.company", string="Company", default=_default_company_id)
    start_date = fields.Date(string="Start Date", required=True, default=fields.Date.today())
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    location_ids = fields.Many2many(comodel_name="stock.location", string="Location")
    product_ids = fields.Many2many(comodel_name="product.product", string="Products")
    file = fields.Binary(string='File')

    # @api.onchange("location_id","company_id")
    # def onchange_location_id(self):
    #     ids_location = []
    #     domain = {}
        
    #     location_ids = self.env['stock.location'].sudo().search([('usage','=','internal'),('company_id','=', self.company_id.id)])
    #     for location in location_ids:
    #         ids_location.append(location.id)

    #     domain['location_id'] = [('id','in', ids_location)]
    #     return {'domain':domain}

    def button_print_excel(self):
        self.ensure_one()

        fp = BytesIO()
        workbook = xlsxwriter.Workbook(fp)
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
        worksheet1.set_column('D:D', 20)
        worksheet1.set_column('E:E', 20)
        worksheet1.set_column('F:F', 20)
        worksheet1.set_column('G:G', 2)
        worksheet1.set_column('H:H', 20)
        worksheet1.set_column('I:I', 20)
        worksheet1.set_column('J:J', 20)
        worksheet1.set_column('K:K', 20)
        worksheet1.set_column('L:L', 20)

        today = (datetime.now() + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
        filename = str(self.company_id.name) + " - Stock Card Report"
        data_report = self.env['dti.global.function.stock.report']._get_stock_card(self.company_id.id, self.start_date, self.end_date, self.location_ids.ids, self.product_ids.ids)
        
        worksheet1.merge_range('A1:J1', 'STOCK CARD REPORT', left_title)
        worksheet1.merge_range('A2:J2', str(self.company_id.name), left_title_sub)
        
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
        worksheet1.write(i, 3, ", ".join(self.location_ids.mapped('display_name')), left_title_sub)
        worksheet1.write(i, 5, 'Printed on', left_title_sub)
        worksheet1.write(i, 6, ':', center_title_sub)
        worksheet1.write(i, 7, datetime.strptime(today, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S") + ' by ' + self.env.user.name, left_title_sub)
        i += 2

        for data in data_report:
            worksheet1.merge_range(i, 0, i, 1, 'Product', header_title)
            worksheet1.write(i, 2, ':', header_title)
            worksheet1.write(i, 3,  str(data['product']) , header_title)
            i += 1
            worksheet1.merge_range(i, 0, i, 1, 'UoM', header_title)
            worksheet1.write(i, 2, ':', header_title)
            worksheet1.write(i, 3, data['uom'], header_title)
            i += 1

            worksheet1.write(i, 0, 'No', header_table)
            worksheet1.merge_range(i, 1, i, 2, 'Date', header_table)
            worksheet1.merge_range(i, 3, i, 4, 'Notes', header_table)
            worksheet1.merge_range(i, 5, i, 6, 'Reference', header_table)
            worksheet1.write(i, 7, 'Move In', header_table)
            worksheet1.write(i, 8, 'Move Out', header_table)
            worksheet1.write(i, 9, 'Balance', header_table)
            worksheet1.write(i, 10, 'Value', header_table)
            worksheet1.write(i, 11, 'Balance Value', header_table)

            i += 1

            for line in data['data_ids']:
                worksheet1.write(i, 0, line['seq'], center_table)
                worksheet1.merge_range(i, 1, i, 2, datetime.strptime(str(line['date']), "%Y-%m-%d %H:%M:%S").\
                                    strftime("%d/%m/%Y") if line['date'] else '', center_table)
                worksheet1.merge_range(i, 3, i, 4, line['operation'] if line['operation'] else '', left_table)
                worksheet1.merge_range(i, 5, i, 6, line['reference'] if line['reference'] else '', left_table)
                worksheet1.write(i, 7, line['move_in'], numb_table)
                worksheet1.write(i, 8, line['move_out'], numb_table)
                worksheet1.write(i, 9, line['balance_qty'], numb_table)
                worksheet1.write(i, 10, line['total_value'], numb_table)
                worksheet1.write(i, 11, line['balance_value'], numb_table)
                i += 1

            worksheet1.write(i, 8, 'Ending Balance', left_footer)
            worksheet1.write(i, 9, data['ending_balance'], numb_footer)
            worksheet1.write(i, 10, 'Ending Value', left_footer)
            worksheet1.write(i, 11, data['ending_value'], numb_footer)
            i += 2

        workbook.close()
        file=base64.encodebytes(fp.getvalue())
        self.write({'file':file})
        fp.close()
        
        return{
            'type' : 'ir.actions.act_url',
            'url': 'web/content/?model=wizard.dti.stock.card.report&field=file&download=true&id=%s&filename=%s.xlsx'%(self.id,filename),
            'target': 'new',
        }
