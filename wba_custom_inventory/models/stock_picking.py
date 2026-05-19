from odoo import models, fields, api, _
from odoo.addons.stock.models.stock_picking import Picking as StockPickingBase



@api.model_create_multi
def create(self, vals_list):
    scheduled_dates = []
    for vals in vals_list:
        # defaults = self.default_get(['name', 'picking_type_id'])
        # picking_type = self.env['stock.picking.type'].browse(vals.get('picking_type_id', defaults.get('picking_type_id')))
        # if vals.get('name', '/') == '/' and defaults.get('name', '/') == '/' and vals.get('picking_type_id', defaults.get('picking_type_id')):
        #     if picking_type.sequence_id:
        #         vals['name'] = picking_type.sequence_id.next_by_id()

        # make sure to write `schedule_date` *after* the `stock.move` creation in
        # order to get a determinist execution of `_set_scheduled_date`
        scheduled_dates.append(vals.pop('scheduled_date', False))

    pickings = super(StockPickingBase,self).create(vals_list)

    for picking, scheduled_date in zip(pickings, scheduled_dates):
        if scheduled_date:
            picking.with_context(mail_notrack=True).write({'scheduled_date': scheduled_date})
    pickings._autoconfirm_picking()

    for picking, vals in zip(pickings, vals_list):
        # set partner as follower
        if vals.get('partner_id'):
            if picking.location_id.usage == 'supplier' or picking.location_dest_id.usage == 'customer':
                picking.message_subscribe([vals.get('partner_id')])
        if vals.get('picking_type_id'):
            for move in picking.move_ids:
                if not move.description_picking:
                    move.description_picking = move.product_id.with_context(lang=move._get_lang())._get_description(move.picking_id.picking_type_id)
    return pickings


def _create_backorder(self):
    """ This method is called when the user chose to create a backorder. It will create a new
    picking, the backorder, and move the stock.moves that are not `done` or `cancel` into it.
    """
    backorders = self.env['stock.picking']
    bo_to_assign = self.env['stock.picking']
    for picking in self:
        moves_to_backorder = picking._get_moves_to_backorder()
        moves_to_backorder._recompute_state()
        if moves_to_backorder:
            backorder_picking = picking._create_backorder_picking()
            moves_to_backorder.write({'picking_id': backorder_picking.id, 'picked': False})
            moves_to_backorder.move_line_ids.package_level_id.write({'picking_id': backorder_picking.id})
            moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
            backorders |= backorder_picking
            picking.message_post(
                body=_('The backorder %s has been created.', backorder_picking._get_html_link())
            )
            if backorder_picking.picking_type_id.reservation_method == 'at_confirm' and backorder_picking.picking_type_id.code != 'outgoing':
                bo_to_assign |= backorder_picking
                
    if bo_to_assign:
        bo_to_assign.action_assign()
    return backorders

StockPickingBase.create = create
StockPickingBase._create_backorder = _create_backorder


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    _sql_constraints = [
        ('name_uniq','CHECK (true)','!'),
    ]


    def _action_done(self):
        res = super()._action_done()
        picking_without_name = self.filtered(lambda p: p.name == '/')
        if picking_without_name:
            for picking in picking_without_name:
                picking.name = picking.picking_type_id.sequence_id.next_by_id()
        return res

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if 'name' not in vals or vals.get('name') == '/':
    #             vals['name'] = '/'
        
    #     return super().create(vals_list)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     pickings = super().create(vals_list)
    #     for picking in pickings:
    #         if picking.state == 'draft':
    #             picking.name = '/'
    #     return pickings

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         vals.setdefault('name', '/')
    #     return super().create(vals_list)