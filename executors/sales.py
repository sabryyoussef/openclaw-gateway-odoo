# -*- coding: utf-8 -*-
"""Sales Orders Executor"""
from .base import BaseExecutor


class SalesOrdersExecutor(BaseExecutor):
    """Executor for querying sales orders"""
    
    def execute(self, env, payload):
        """
        Query sales orders.
        
        Args:
            env: Odoo environment
            payload (dict): {
                'limit': int (optional, default 10),
                'state': str (optional, filter by state),
                'partner_id': int (optional, filter by customer)
            }
            
        Returns:
            dict: {'success': True, 'data': {'orders': [...], 'count': int}}
        """
        limit = self._validate_limit(payload.get('limit'), 100)
        
        # Build domain
        domain = []
        if payload.get('state'):
            domain.append(('state', '=', payload['state']))
        if payload.get('partner_id'):
            domain.append(('partner_id', '=', int(payload['partner_id'])))
        
        try:
            # Query orders
            SaleOrder = env['sale.order'].sudo()
            orders = SaleOrder.search(domain, limit=limit, order='date_order desc')
            
            # Format results
            orders_data = []
            for order in orders:
                orders_data.append({
                    'id': order.id,
                    'name': order.name,
                    'partner_id': order.partner_id.id,
                    'partner_name': order.partner_id.name,
                    'date_order': self._format_date(order.date_order),
                    'state': order.state,
                    'amount_total': order.amount_total,
                    'currency': self._safe_field_value(order, 'currency_id'),
                    'user_id': self._safe_field_value(order, 'user_id'),
                })
            
            return self._format_response(
                success=True,
                data={
                    'orders': orders_data,
                    'count': len(orders_data),
                    'total_available': SaleOrder.search_count(domain)
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to query sales orders: {str(e)}'
            )
