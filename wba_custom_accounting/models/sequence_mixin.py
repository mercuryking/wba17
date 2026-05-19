from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date
from odoo.tools import frozendict, mute_logger, date_utils

import re
from collections import defaultdict
from psycopg2 import sql, DatabaseError

class SequenceMixin(models.AbstractModel):
    _inherit = 'sequence.mixin'

    _sequence_monthly_regex_reverse = r'^(?P<prefix1>.*?)(?P<seq>\d+)(?P<prefix2>\D+?)(?P<month>(0[1-9]|1[0-2]))(?P<prefix3>\D+?)(?P<year>((?<=\D)|(?<=^))((19|20|21)\d{2}|(\d{2}(?=\D))))(?P<suffix>\D*?)$'
    _sequence_yearly_regex_reverse = r'^(?P<prefix1>.*?)(?P<seq>\d+)(?P<prefix2>\D+?)(?P<year>((?<=\D)|(?<=^))((19|20|21)?\d{2}))(?P<suffix>\D*?)$'

    @api.model
    def _deduce_sequence_number_reset(self, name):
        """Detect if the used sequence resets yearly, montly or never.

        :param name: the sequence that is used as a reference to detect the resetting
            periodicity. Typically, it is the last before the one you want to give a
            sequence.
        """
        for regex, ret_val, requirements in [
            (self._sequence_monthly_regex_reverse, 'month', ['seq', 'month', 'year']),
            (self._sequence_monthly_regex, 'month', ['seq', 'month', 'year']),
            (self._sequence_year_range_regex, 'year_range', ['seq', 'year', 'year_end']),
            (self._sequence_yearly_regex, 'year', ['seq', 'year']),
            (self._sequence_yearly_regex_reverse, 'year', ['seq', 'year']),
            (self._sequence_fixed_regex, 'never', ['seq']),
        ]:
            match = re.match(regex, name or '')
            if match:
                groupdict = match.groupdict()
                if (
                    groupdict.get('year_end') and groupdict.get('year')
                    and (
                        len(groupdict['year']) < len(groupdict['year_end'])
                        or self._truncate_year_to_length((int(groupdict['year']) + 1), len(groupdict['year_end'])) != int(groupdict['year_end'])
                    )
                ):
                    # year and year_end are not compatible for range (the difference is not 1)
                    continue
                if all(groupdict.get(req) is not None for req in requirements):
                    return ret_val
        raise ValidationError(_(
            'The sequence regex should at least contain the seq grouping keys. For instance:\n'
            r'^(?P<prefix1>.*?)(?P<seq>\d*)(?P<suffix>\D*?)$'
        ))

    def _get_sequence_format_param(self, previous):
        """Get the python format and format values for the sequence.

        :param previous: the sequence we want to extract the format from
        :return tuple(format, format_values):
            format is the format string on which we should call .format()
            format_values is the dict of values to format the `format` string
            ``format.format(**format_values)`` should be equal to ``previous``
        """
        sequence_number_reset = self._deduce_sequence_number_reset(previous)
        regex = self._sequence_fixed_regex
        if sequence_number_reset == 'year':
            # Try yearly_regex_reverse first if it matches
            if re.match(self._sequence_yearly_regex_reverse, previous):
                regex = self._sequence_yearly_regex_reverse
            else:
                regex = self._sequence_yearly_regex
        elif sequence_number_reset == 'year_range':
            regex = self._sequence_year_range_regex
        elif sequence_number_reset == 'month':
            # Try monthly_regex_reverse first if it matches
            if re.match(self._sequence_monthly_regex_reverse, previous):
                regex = self._sequence_monthly_regex_reverse
            else:
                regex = self._sequence_monthly_regex
        format_values = re.match(regex, previous).groupdict()
        format_values['seq_length'] = len(format_values['seq'])
        format_values['year_length'] = len(format_values.get('year') or '')
        format_values['year_end_length'] = len(format_values.get('year_end') or '')
        if not format_values.get('seq') and 'prefix1' in format_values and 'suffix' in format_values:
            # if we don't have a seq, consider we only have a prefix and not a suffix
            format_values['prefix1'] = format_values['suffix']
            format_values['suffix'] = ''
        for field in ('seq', 'year', 'month', 'year_end'):
            format_values[field] = int(format_values.get(field) or 0)

        placeholders = re.findall(r'\b(prefix\d|seq|suffix\d?|year|year_end|month)\b', regex)
        format = ''.join(
            "{seq:0{seq_length}d}" if s == 'seq' else
            "{month:02d}" if s == 'month' else
            "{year:0{year_length}d}" if s == 'year' else
            "{year_end:0{year_end_length}d}" if s == 'year_end' else
            "{%s}" % s
            for s in placeholders
        )
        return format, format_values


    @api.depends(lambda self: [self._sequence_field])
    def _compute_split_sequence(self):
        super()._compute_split_sequence()
        for record in self:
            sequence = record[record._sequence_field] or ''
            # Detect which regex pattern matches to properly extract seq
            regex_to_use = record._sequence_fixed_regex
            
            # Try to match reverse patterns first (SEQ comes before YEAR/MONTH)
            if re.match(record._sequence_monthly_regex_reverse, sequence):
                regex_to_use = record._sequence_monthly_regex_reverse
            elif re.match(record._sequence_yearly_regex_reverse, sequence):
                regex_to_use = record._sequence_yearly_regex_reverse
            elif re.match(record._sequence_monthly_regex, sequence):
                regex_to_use = record._sequence_monthly_regex
            elif re.match(record._sequence_yearly_regex, sequence):
                regex_to_use = record._sequence_yearly_regex
            elif re.match(record._sequence_year_range_regex, sequence):
                regex_to_use = record._sequence_year_range_regex
            
            regex = re.sub(r"\?P<\w+>", "?:", regex_to_use.replace(r"?P<seq>", ""))  # make the seq the only matching group
            matching = re.match(regex, sequence)
            if matching and matching.lastindex:
                record.sequence_prefix = sequence[:matching.start(1)]
                record.sequence_number = int(matching.group(1) or 0)
            else:
                record.sequence_prefix = ''
                record.sequence_number = 0