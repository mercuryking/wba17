# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.tools import get_lang
from odoo.exceptions import UserError

from datetime import timedelta
from collections import defaultdict
import re


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportLineName': 'account_reports_gl_by_date.GeneralLedgerLineName',
            },
        }

    def _get_aml_group_date_values(self, report, options, expanded_account_ids, offset=0, limit=None):
        rslt = {account_id: {} for account_id in expanded_account_ids}
        aml_query, aml_params = self._get_group_date_query_amls(report, options, expanded_account_ids, offset=offset, limit=limit)
        self._cr.execute(aml_query, aml_params)
        aml_results_number = 0
        has_more = False
        for aml_result in self._cr.dictfetchall():
            aml_results_number += 1
            if aml_results_number == limit:
                has_more = True
                break

            
            # The same aml can return multiple results when using account_report_cash_basis module, if the receivable/payable
            # is reconciled with multiple payments. In this case, the date shown for the move lines actually corresponds to the
            # reconciliation date. In order to keep distinct lines in this case, we include date in the grouping key.
            aml_key = aml_result['date']

            account_result = rslt[aml_result['account_id']]
            if not aml_key in account_result:
                account_result[aml_key] = {col_group_key: {} for col_group_key in options['column_groups']}

            already_present_result = account_result[aml_key][aml_result['column_group_key']]
            if already_present_result:
                # In case the same move line gives multiple results at the same date, add them.
                # This does not happen in standard GL report, but could because of custom shadowing of account.move.line,
                # such as the one done in account_report_cash_basis (if the payable/receivable line is reconciled twice at the same date).
                already_present_result['debit'] += aml_result['debit']
                already_present_result['credit'] += aml_result['credit']
                already_present_result['balance'] += aml_result['balance']
                # already_present_result['amount_currency'] += aml_result['amount_currency']
            else:
                account_result[aml_key][aml_result['column_group_key']] = aml_result

        return rslt, has_more

        
    def _get_group_date_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        """ Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:               The report options.
        :param expanded_account_ids:  The account.account ids corresponding to consider. If None, match every account.
        :param offset:                The offset of the query (used by the load more).
        :param limit:                 The limit of the query (used by the load more).
        :return:                      (query, params)
        """
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        all_params = []
        lang = self.env.user.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'account.name'
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            # Get sums for the account move lines.
            # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
            tables, where_clause, where_params = report._query_get(group_options, domain=additional_domain, date_scope='strict_range')
            ct_query = report._get_query_currency_table(group_options)
            query = f'''
                (SELECT
                account_move_line.date as date,
                account_move_line.account_id as account_id,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance,
                %s AS column_group_key
                FROM {tables}
                JOIN account_move move                      ON move.id = account_move_line.move_id
                LEFT JOIN {ct_query}                        ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE {where_clause}
                GROUP BY account_move_line.date, account_move_line.account_id
                ORDER BY account_move_line.date, account_move_line.account_id)
            '''

            queries.append(query)
            all_params.append(column_group_key)
            all_params += where_params

        full_query = " UNION ALL ".join(queries)

        if offset:
            full_query += ' OFFSET %s '
            all_params.append(offset)
        if limit:
            full_query += ' LIMIT %s '
            all_params.append(limit)

        return (full_query, all_params)


    

    def _get_aml_group_by_date_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        line_columns = []
        for column in options['columns']:
            col_expr_label = column['expression_label']
            col_value = eval_dict[column['column_group_key']].get(col_expr_label)
            col_currency = None

            if col_value is not None:
                if col_expr_label == 'amount_currency':
                    col_currency = self.env['res.currency'].browse(eval_dict[column['column_group_key']]['currency_id'])
                    col_value = None if col_currency == self.env.company.currency_id else col_value
                elif col_expr_label == 'balance':
                    col_value += (init_bal_by_col_group[column['column_group_key']] or 0)

            line_columns.append(report._build_column_dict(
                col_value,
                column,
                options=options,
                currency=col_currency,
            ))

        aml_id = None
        move_name = None
        caret_type = None
        for column_group_dict in eval_dict.values():
            
            date = str(column_group_dict.get('date', ''))
            move_name = date
            aml_id = 'account_by_date' + date

        return {
            'id': report._get_generic_line_id(None, aml_id, parent_line_id=parent_line_id, markup=date),
            'caret_options': caret_type,
            'parent_id': parent_line_id,
            'name': move_name,
            'columns': line_columns,
            'unfoldable': True,
            'disable_open_journal_item': True,
            'unfolded': False,
            'level': 3,
            'expand_function': '_report_expand_unfoldable_line_general_ledger',
        }

    def _get_account_title_line(self, report, options, account, has_lines, eval_dict):

        res = super(GeneralLedgerCustomHandler, self)._get_account_title_line(report, options, account, has_lines, eval_dict)
        # print("options===================", options)
        # if not self._context.get('is_export', False):
        if options.get('export_mode', False) :
            res['expand_function'] = '_report_expand_unfoldable_line_general_ledger'
        else:
            res['expand_function'] = '_report_expand_unfoldable_line_group_by_date_general_ledger'
        return res

    def _report_expand_unfoldable_line_group_by_date_general_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in  zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }


        report = self.env.ref('account_reports.general_ledger_report')
        model, model_id = report._get_model_info_from_id(line_dict_id)
        if model != 'account.account':
            raise UserError(_("Wrong ID for general ledger line to expand: %s", line_dict_id))

        lines = []
        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                account, init_balance_by_col_group = unfold_all_batch_data['initial_balances'][model_id]
            else:
                account, init_balance_by_col_group = self._get_initial_balance_values(report, [model_id], options)[model_id]

            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, account.currency_id)

            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        # Get move lines
        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_results'][model_id]
            has_more = unfold_all_batch_data['has_more'].get(model_id, False)
        else:
            aml_results, has_more = self._get_aml_group_date_values(report, options, [model_id], offset=offset, limit=limit_to_load)
            aml_results = aml_results[model_id]

        next_progress = progress

        for aml_result in aml_results.values():
            
            new_line = self._get_aml_group_by_date_line(report, line_dict_id, options, aml_result, next_progress)
            balance = 0
            for column in new_line['columns']:
                if column['expression_label'] == 'balance':
                    balance += next_progress[column['column_group_key']]
            lines.append(new_line)
          

            next_progress = init_load_more_progress(new_line)

        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': next_progress,
        }
    
    
    def _get_initial_balance_values(self, report, account_ids, options):
        """
        Get sums for the initial balance.
        """
        queries = []
        params = []
        for column_group_key, options_group in report._split_options_per_column_group(options).items():
            if options['date']['date_from'] != options_group['date']['date_from']:
                options_group['date']['date_from'] = options['date']['date_from']
            if options['date']['date_to'] != options_group['date']['date_to']:
                options_group['date']['date_to'] = options['date']['date_to']
            new_options = self._get_options_initial_balance(options_group)
            ct_query = report._get_query_currency_table(new_options)
            domain = [('account_id', 'in', account_ids)]
            if new_options.get('include_current_year_in_unaff_earnings'):
                domain += [('account_id.include_initial_balance', '=', True)]
            tables, where_clause, where_params = report._query_get(new_options, 'normal', domain=domain)
            params.append(column_group_key)
            params += where_params
            queries.append(f"""
                SELECT
                    account_move_line.account_id                                                          AS groupby,
                    'initial_balance'                                                                     AS key,
                    NULL                                                                                  AS max_date,
                    %s                                                                                    AS column_group_key,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)                                 AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM {tables}
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                GROUP BY account_move_line.account_id
            """)

        self._cr.execute(" UNION ALL ".join(queries), params)

        init_balance_by_col_group = {
            account_id: {column_group_key: {} for column_group_key in options['column_groups']}
            for account_id in account_ids
        }
        for result in self._cr.dictfetchall():
            init_balance_by_col_group[result['groupby']][result['column_group_key']] = result

        accounts = self.env['account.account'].browse(account_ids)
        return {
            account.id: (account, init_balance_by_col_group[account.id])
            for account in accounts
        }

    
    def _report_expand_unfoldable_line_general_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in  zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }


        report = self.env.ref('account_reports.general_ledger_report')
        model, model_id = report._get_model_info_from_id(line_dict_id)

        account_match = re.search(r'~account\.account~(\d+)', line_dict_id)
        account_number = account_match.group(1) if account_match else None

        # Ambil tanggal paling ujung (tanggal terakhir)
        date_match = re.findall(r'\d{4}-\d{2}-\d{2}', line_dict_id)
        last_date = date_match[-1] if date_match else None
        if model != 'account.account' and last_date:
            model = 'account.account'
            model_id = int(account_number) if account_number else None

        if last_date:
            options['date']['date_from'] = last_date
            options['date']['date_to'] = last_date
        if not model_id:
            raise UserError(_("Wrong ID for general ledger line to expand: %s", line_dict_id))

        lines = []
        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                account, init_balance_by_col_group = unfold_all_batch_data['initial_balances'][model_id]
            else:
                account, init_balance_by_col_group = self._get_initial_balance_values(report, [model_id], options)[model_id]

            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, account.currency_id)

            if initial_balance_line:
                if options.get('export_mode', False):
                    lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)
        
        
        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and options['export_mode'] != 'print' else None
        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_results'][model_id]
            has_more = unfold_all_batch_data['has_more'].get(model_id, False)
        else:
            aml_results, has_more = self._get_aml_values(report, options, [model_id], offset=offset, limit=limit_to_load)
            aml_results = aml_results[model_id]



        next_progress = progress


        for aml_result in aml_results.values():
            
            new_line = self._get_aml_line(report, line_dict_id, options, aml_result, next_progress)
            balance = 0
            for column in new_line['columns']:
                if column['expression_label'] == 'balance':
                    balance += next_progress[column['column_group_key']]

            lines.append(new_line)
          

            next_progress = init_load_more_progress(new_line)


        return {
            'lines': lines,
            'offset_increment': report.load_more_limit,
            'has_more': has_more,
            'progress': next_progress,
        }
    


    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        """ Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:               The report options.
        :param expanded_account_ids:  The account.account ids corresponding to consider. If None, match every account.
        :param offset:                The offset of the query (used by the load more).
        :param limit:                 The limit of the query (used by the load more).
        :return:                      (query, params)
        """
        additional_domain = [('account_id', 'in', expanded_account_ids)] if expanded_account_ids is not None else None
        queries = []
        all_params = []
        lang = self.env.user.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'account.name'
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            # Get sums for the account move lines.
            # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
            if options['date']['date_from'] != group_options['date']['date_from']:
                group_options['date']['date_from'] = options['date']['date_from']
            if options['date']['date_to'] != group_options['date']['date_to']:
                group_options['date']['date_to'] = options['date']['date_to']

            tables, where_clause, where_params = report._query_get(group_options, domain=additional_domain, date_scope='strict_range')
            ct_query = report._get_query_currency_table(group_options)
            query = f'''
                (SELECT
                    account_move_line.id,
                    account_move_line.date,
                    account_move_line.date_maturity,
                    account_move_line.name,
                    account_move_line.ref,
                    account_move_line.company_id,
                    account_move_line.account_id,
                    account_move_line.payment_id,
                    account_move_line.partner_id,
                    account_move_line.currency_id,
                    account_move_line.amount_currency,
                    COALESCE(account_move_line.invoice_date, account_move_line.date)                 AS invoice_date,
                    ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                    ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                    ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                    move.name                               AS move_name,
                    company.currency_id                     AS company_currency_id,
                    partner.name                            AS partner_name,
                    move.move_type                          AS move_type,
                    account.code                            AS account_code,
                    {account_name}                          AS account_name,
                    journal.code                            AS journal_code,
                    {journal_name}                          AS journal_name,
                    full_rec.id                             AS full_rec_name,
                    %s                                      AS column_group_key
                FROM {tables}
                JOIN account_move move                      ON move.id = account_move_line.move_id
                LEFT JOIN {ct_query}                        ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
                WHERE {where_clause}
                ORDER BY account_move_line.date, account_move_line.move_name, account_move_line.id)
            '''

            queries.append(query)
            all_params.append(column_group_key)
            all_params += where_params

        full_query = " UNION ALL ".join(queries)

        if offset:
            full_query += ' OFFSET %s '
            all_params.append(offset)
        if limit:
            full_query += ' LIMIT %s '
            all_params.append(limit)

        return (full_query, all_params)
   
    def _get_aml_line(self, report, parent_line_id, options, eval_dict, init_bal_by_col_group):
        aml_line = super(GeneralLedgerCustomHandler, self)._get_aml_line(report, parent_line_id, options, eval_dict, init_bal_by_col_group)
        aml_line['level'] = 4
        return aml_line
    

    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        account_ids_to_expand = []
        if options.get('export_mode', False):
            for line_dict in lines_to_expand_by_function.get('_report_expand_unfoldable_line_general_ledger', []):
                model, model_id = report._get_model_info_from_id(line_dict['id'])
                if model == 'account.account':
                    account_ids_to_expand.append(model_id)

            limit_to_load = report.load_more_limit if report.load_more_limit and not options.get('export_mode') else None
            has_more_per_account_id = {}
            unlimited_aml_results_per_account_id = self._get_aml_values(report, options, account_ids_to_expand)[0] 
        else:

            for line_dict in lines_to_expand_by_function.get('_report_expand_unfoldable_line_group_by_date_general_ledger', []):
                model, model_id = report._get_model_info_from_id(line_dict['id'])
                if model == 'account.account':
                    account_ids_to_expand.append(model_id)

            limit_to_load = report.load_more_limit if report.load_more_limit and not options.get('export_mode') else None
            has_more_per_account_id = {}
            unlimited_aml_results_per_account_id = self._get_aml_group_date_values(report, options, account_ids_to_expand)[0]
        
        if limit_to_load:
            # Apply the load_more_limit.
            # load_more_limit cannot be passed to the call to _get_aml_values, otherwise it won't be applied per account but on the whole result.
            # We gain perf from batching, but load every result ; then we need to filter them.

            aml_results_per_account_id = {}
            for account_id, account_aml_results in unlimited_aml_results_per_account_id.items():
                account_values = {}
                for key, value in account_aml_results.items():
                    if len(account_values) == limit_to_load:
                        has_more_per_account_id[account_id] = True
                        break
                    account_values[key] = value
                aml_results_per_account_id[account_id] = account_values
        else:
            aml_results_per_account_id = unlimited_aml_results_per_account_id
        return {
            'initial_balances': self._get_initial_balance_values(report, account_ids_to_expand, options),
            'aml_results': aml_results_per_account_id,
            'has_more': has_more_per_account_id,
        }
    
    def open_journal_items(self, options, params):
        report = self.env['account.report'].browse(options['report_id'])
        record_model, record_id = report._get_model_info_from_id(params.get('line_id'))
        if not record_model:
            if isinstance(record_id, str) and "account_by_date" in record_id:
                date_to = record_id.split("account_by_date")[-1]
                date_from = date_to
                options['date']['date_from'] = date_from
                options['date']['date_to'] = date_to
                params['line_id'] = params['line_id'].split(f"|{date_to}")[0]
        return report.open_journal_items(options=options, params=params)
