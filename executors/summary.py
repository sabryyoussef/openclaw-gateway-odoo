# -*- coding: utf-8 -*-
"""Summary Executor - Database Statistics"""
from .base import BaseExecutor


class SummaryExecutor(BaseExecutor):
    """Executor for database summary statistics"""
    
    def execute(self, env, payload):
        """
        Get database statistics.
        
        Args:
            env: Odoo environment
            payload (dict): Not used
            
        Returns:
            dict: {'success': True, 'data': {'counts': {...}}}
        """
        try:
            # Count records in major models
            counts = {
                'sales_orders': env['sale.order'].sudo().search_count([]),
                'invoices': env['account.move'].sudo().search_count([
                    ('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])
                ]),
                'customers': env['res.partner'].sudo().search_count([('customer_rank', '>', 0)]),
                'employees': env['hr.employee'].sudo().search_count([]),
                'products': env['product.product'].sudo().search_count([]),
                'users': env['res.users'].sudo().search_count([('active', '=', True)]),
                'leads': env['crm.lead'].sudo().search_count([]),
            }
            
            return self._format_response(
                success=True,
                data={'counts': counts}
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to get summary: {str(e)}'
            )
