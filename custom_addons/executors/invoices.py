# -*- coding: utf-8 -*-
"""Invoices Executor"""
from .base import BaseExecutor


class InvoicesExecutor(BaseExecutor):
    """Executor for querying invoices"""
    
    def execute(self, env, payload):
        """
        Query invoices.
        
        Args:
            env: Odoo environment
            payload (dict): {
                'limit': int (optional, default 10),
                'state': str (optional, filter by state),
                'partner_id': int (optional, filter by customer),
                'move_type': str (optional, filter by type: out_invoice, in_invoice, etc.)
            }
            
        Returns:
            dict: {'success': True, 'data': {'invoices': [...], 'count': int}}
        """
        limit = self._validate_limit(payload.get('limit'), 100)
        
        # Build domain - only get invoices, not other account moves
        domain = [('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])]
        
        if payload.get('state'):
            domain.append(('state', '=', payload['state']))
        if payload.get('partner_id'):
            domain.append(('partner_id', '=', int(payload['partner_id'])))
        if payload.get('move_type'):
            domain = [('move_type', '=', payload['move_type'])]
        
        try:
            # Query invoices
            AccountMove = env['account.move'].sudo()
            invoices = AccountMove.search(domain, limit=limit, order='invoice_date desc')
            
            # Format results
            invoices_data = []
            for invoice in invoices:
                invoices_data.append({
                    'id': invoice.id,
                    'name': invoice.name,
                    'partner_id': invoice.partner_id.id,
                    'partner_name': invoice.partner_id.name,
                    'invoice_date': self._format_date(invoice.invoice_date),
                    'invoice_date_due': self._format_date(invoice.invoice_date_due),
                    'state': invoice.state,
                    'move_type': invoice.move_type,
                    'amount_total': invoice.amount_total,
                    'amount_residual': invoice.amount_residual,
                    'currency': self._safe_field_value(invoice, 'currency_id'),
                    'payment_state': invoice.payment_state,
                })
            
            return self._format_response(
                success=True,
                data={
                    'invoices': invoices_data,
                    'count': len(invoices_data),
                    'total_available': AccountMove.search_count(domain)
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to query invoices: {str(e)}'
            )
