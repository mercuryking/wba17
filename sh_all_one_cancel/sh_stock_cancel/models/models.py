# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models

class Move(models.Model):
    _inherit = 'stock.move'

    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search([('name','=','stock_account')],limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True


    def _sh_unreseve_qty(self):
        for move_line in self.sudo().mapped('move_line_ids'):
            # unreserve qty
            quant_source = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                        ('product_id', '=',
                                                            move_line.product_id.id),
                                                        ('lot_id', '=', move_line.lot_id.id)], limit=1)
            quant_dest = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                        ('product_id', '=',
                                                            move_line.product_id.id),
                                                        ('lot_id', '=', move_line.lot_id.id)], limit=1)
            if move_line.state == 'done':

                if quant_source:
                    quant_source.write({'quantity': quant_source.quantity + move_line.quantity})
                else:
                    self.env['stock.quant'].sudo().create({
                        'product_id': move_line.product_id.id,
                        'location_id': move_line.location_id.id,
                        'quantity': move_line.quantity,
                        'lot_id': move_line.lot_id.id,
                    })


                if quant_dest:
                    quant_dest.write({'quantity': quant_dest.quantity - move_line.quantity})
                else:
                    self.env['stock.quant'].sudo().create({
                        'product_id': move_line.product_id.id,
                        'location_id': move_line.location_dest_id.id,
                        'quantity': -move_line.quantity,
                        'lot_id': move_line.lot_id.id,
                    })


            elif move_line.state != 'cancel':
                move_line.move_id._do_unreserve()
                # quant_dest.write({'reserved_quantity': quant_dest.reserved_quantity - move_line.product_uom_qty})

    def action_move_cancel(self):
        for rec in self:
            rec.sudo().write({'state': 'cancel'})
            rec.mapped('move_line_ids').sudo().write({'state': 'cancel'})
            rec._sh_unreseve_qty()

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('account_move_ids')
                account_move_line_ids = account_move.sudo().mapped('line_ids')
                reconcile_ids = []
                if account_move_line_ids:
                    reconcile_ids = account_move_line_ids.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                account_move.sudo().write({'state':'draft','name':'/'})
                account_move.sudo().with_context({'force_delete':True}).unlink()
            
                # cancel stock valuation
                stock_valuation_layer_ids = rec.sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

    def action_move_cancel_draft(self):
        for rec in self:
            rec.sudo().write({'state': 'draft'})
            rec.mapped('move_line_ids').sudo().write({'state': 'draft'})
            rec._sh_unreseve_qty()

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('account_move_ids')
                account_move_line_ids = account_move.sudo().mapped('line_ids')
                reconcile_ids = []
                if account_move_line_ids:
                    reconcile_ids = account_move_line_ids.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                account_move.sudo().write({'state':'draft','name':'/'})
                account_move.sudo().with_context({'force_delete':True}).unlink()
            
                # cancel stock valuation
                stock_valuation_layer_ids = rec.sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

    def action_move_cancel_delete(self):
        for rec in self:
            rec.sudo().write({'state': 'draft'})
            rec.mapped('move_line_ids').sudo().write({'state': 'draft'})
            rec._sh_unreseve_qty()

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('account_move_ids')
                account_move_line_ids = account_move.sudo().mapped('line_ids')
                reconcile_ids = []
                if account_move_line_ids:
                    reconcile_ids = account_move_line_ids.sudo().mapped('id')
                reconcile_lines = self.env['account.partial.reconcile'].sudo().search(['|',('credit_move_id','in',reconcile_ids),('debit_move_id','in',reconcile_ids)])
                if reconcile_lines:
                    reconcile_lines.sudo().unlink()
                account_move.mapped('line_ids.analytic_line_ids').sudo().unlink()
                account_move.sudo().write({'state':'draft','name':'/'})
                account_move.sudo().with_context({'force_delete':True}).unlink()
            
                # cancel stock valuation
                stock_valuation_layer_ids = rec.sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()
            rec.mapped('move_line_ids').sudo().unlink()
            rec.sudo().unlink()


class Picking(models.Model):
    _inherit = 'stock.picking'

    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search([('name','=','stock_account')],limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True

    def action_picking_cancel(self):
        if self.date_backdating:
            date_backdating = self.date_backdating 
            accounting_date = date_backdating.date()
            self = self.with_context(manual_validate_date_time=date_backdating, force_period_date=accounting_date)
        
        self.move_ids.filtered(lambda m: m.state != 'cancel').write({
            'quantity' : 0,
            
        })
        self.write({
            'state' : 'cancel'
        })
        self.move_ids.write({
            'state' : 'cancel',
        })
        
        # self.move_ids.stock_valuation_layer_ids.sudo().account_move_id.filtered(lambda m: m.state != 'cancel').button_cancel()
        # self.move_ids.stock_valuation_layer_ids.sudo().account_move_id.unlink()
        # self.move_ids.stock_valuation_layer_ids.sudo().unlink()


    def action_picking_cancel_draft(self):
        self.action_picking_cancel()

        self.move_ids.write({
                'state' : 'draft',
                'picked' : False
            })

        self.move_ids.filtered(lambda m: m.state != 'cancel').move_line_ids.unlink()

                        
        self.sudo().write({'state': 'draft'})

    def action_picking_cancel_delete(self):
        self.action_picking_cancel()
        
        self.sudo().unlink()

    def _sh_unreseve_qty(self):
        
        # done_moves = self.move_ids_without_package.filtered(lambda x: x.state == 'done')
        # not_cancel_move = self.move_ids_without_package.filtered(lambda x: x.state != 'cancel')
        # not_cancel_move -= done_moves

        # not_cancel_move._do_unreserve()

        # for move in done_moves:
        #     old_quantity = move.quantity

        #     move.move_line_ids.write({'quantity': 0})
        #     move.write({'state': 'cancel'})
        #     move.write({'quantity': old_quantity})



        for move_line in self.sudo().mapped('move_ids_without_package').mapped('move_line_ids'):
            # unreserve qty
            quant_source = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                        ('product_id', '=',
                                                            move_line.product_id.id),
                                                        ('lot_id', '=', move_line.lot_id.id)], limit=1)
            quant_dest = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                        ('product_id', '=',
                                                            move_line.product_id.id),
                                                        ('lot_id', '=', move_line.lot_id.id)], limit=1)
            if move_line.state == 'done':

                if quant_source:
                    quant_source.write({'quantity': quant_source.quantity + move_line.quantity})
                else:
                    self.env['stock.quant'].sudo().create({
                        'product_id': move_line.product_id.id,
                        'location_id': move_line.location_id.id,
                        'quantity': move_line.quantity,
                        'lot_id': move_line.lot_id.id,
                    })


                if quant_dest:
                    quant_dest.write({'quantity': quant_dest.quantity - move_line.quantity})
                else:
                    self.env['stock.quant'].sudo().create({
                        'product_id': move_line.product_id.id,
                        'location_id': move_line.location_dest_id.id,
                        'quantity': -move_line.quantity,
                        'lot_id': move_line.lot_id.id,
                    })


            elif move_line.state != 'cancel':
                move_line.move_id._do_unreserve()

    def sh_cancel(self):

        self.action_picking_cancel()
        

        if self.company_id.picking_operation_type == 'cancel':
            return {
                'name': 'Inventory Transfer',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_type': 'form',
                'view_mode': 'tree,kanban,form',
                'target': 'current',
            }
            

        elif self.company_id.picking_operation_type == 'cancel_delete':
            # cancel packages
           
            self.sudo().unlink()

            return {
                'name': 'Inventory Transfer',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_type': 'form',
                'view_mode': 'tree,kanban,form',
                'target': 'current',
            }


        elif self.company_id.picking_operation_type == 'cancel_draft':
            # cancel packages
            self.move_ids.filtered(lambda m: m.state != 'cancel').write({
                'quantity' : 0,
                'state' : 'draft',
                'picked' : False
            })
                        
            self.sudo().write({'state': 'draft'})
