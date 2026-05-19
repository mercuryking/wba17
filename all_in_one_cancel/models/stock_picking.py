from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_force_reset_draft(self):
        for picking in self:
            if picking.state == 'cancel':
                picking.write({'state': 'draft'})
                picking.move_ids.write({'state': 'draft'})
                continue
            
            # If picking is DONE, we need more aggressive reset
            if picking.state == 'done':
                # 0. Restore physical quantities (stock.quant)
                Quant = self.env['stock.quant'].sudo()
                for move in picking.move_ids:
                    for sml in move.move_line_ids:
                        if sml.state == 'done' and sml.quantity > 0:
                            # Put stock back to source location
                            Quant._update_available_quantity(
                                sml.product_id, 
                                sml.location_id, 
                                sml.quantity, 
                                lot_id=sml.lot_id, 
                                package_id=sml.package_id, 
                                owner_id=sml.owner_id
                            )
                            # Remove stock from destination location
                            Quant._update_available_quantity(
                                sml.product_id, 
                                sml.location_dest_id, 
                                -sml.quantity, 
                                lot_id=sml.lot_id, 
                                package_id=sml.package_id, 
                                owner_id=sml.owner_id
                            )

                # 1. Handle Account Moves first (Reverse or set to Draft)
                for move in picking.move_ids:
                    # Cancel SVL and related Account Moves
                    svls = move.stock_valuation_layer_ids
                    for svl in svls:
                        if svl.account_move_id:
                            # In Odoo 17, we reset to draft then cancel
                            svl.account_move_id.button_draft()
                            svl.account_move_id.button_cancel()

                        # Restore remaining_qty on incoming layers before unlinking
                        if svl.quantity < 0:
                            abs_qty = abs(svl.quantity)
                            # Find layers of the same product that were depleted
                            product_layers = self.env['stock.valuation.layer'].sudo().search([
                                ('product_id', '=', svl.product_id.id),
                                ('quantity', '>', 0),
                                ('company_id', '=', svl.company_id.id),
                            ], order='create_date desc')
                            
                            for p_layer in product_layers:
                                if abs_qty <= 0:
                                    break
                                missing_qty = p_layer.quantity - p_layer.remaining_qty
                                if missing_qty > 0:
                                    restore_qty = min(abs_qty, missing_qty)
                                    unit_cost = p_layer.value / p_layer.quantity if p_layer.quantity else 0
                                    restore_val = restore_qty * unit_cost
                                    
                                    p_layer.write({
                                        'remaining_qty': p_layer.remaining_qty + restore_qty,
                                        'remaining_value': p_layer.remaining_value + restore_val
                                    })
                                    abs_qty -= restore_qty
                        
                        svl.sudo().unlink()

                # 2. Reset Move States
                picking.move_ids.write({'state': 'draft'})
                # Clear done quantities
                picking.move_ids.write({'quantity': 0, 'picked': False})
                picking.move_line_ids.write({'quantity': 0, 'state': 'draft'})
                
                # 3. Reset Picking State
                picking.write({'state': 'draft', 'date_done': False})
                
                # 4. Safety net: clear any negative reservations caused by state forcing
                self.env.cr.execute(
                    "UPDATE stock_quant SET reserved_quantity = 0 WHERE reserved_quantity < 0 AND company_id = %s", 
                    [picking.company_id.id]
                )
            else:
                # For other states (Assigned, Confirmed), just reset
                picking.action_cancel()
                picking.write({'state': 'draft'})
                picking.move_ids.write({'state': 'draft'})

        return True
