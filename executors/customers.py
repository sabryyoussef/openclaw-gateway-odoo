# -*- coding: utf-8 -*-
"""Customers Executor"""
from .base import BaseExecutor


class CustomersExecutor(BaseExecutor):
    """Executor for querying customers"""
    
    def execute(self, env, payload):
        """
        Query customers (partners).
        
        Args:
            env: Odoo environment
            payload (dict): {
                'limit': int (optional, default 10),
                'is_company': bool (optional, filter companies only),
                'country_id': int (optional, filter by country),
                'search': str (optional, search in name/email)
            }
            
        Returns:
            dict: {'success': True, 'data': {'customers': [...], 'count': int}}
        """
        limit = self._validate_limit(payload.get('limit'), 100)
        
        # Build domain - only get customers, not suppliers or other partners
        domain = [('customer_rank', '>', 0)]
        
        if payload.get('is_company') is not None:
            domain.append(('is_company', '=', bool(payload['is_company'])))
        if payload.get('country_id'):
            domain.append(('country_id', '=', int(payload['country_id'])))
        if payload.get('search'):
            search_term = payload['search']
            domain.append('|')
            domain.append(('name', 'ilike', search_term))
            domain.append(('email', 'ilike', search_term))
        
        try:
            # Query customers
            Partner = env['res.partner'].sudo()
            customers = Partner.search(domain, limit=limit, order='name asc')
            
            # Format results
            customers_data = []
            for customer in customers:
                customers_data.append({
                    'id': customer.id,
                    'name': customer.name,
                    'email': customer.email,
                    'phone': customer.phone,
                    'mobile': customer.mobile,
                    'is_company': customer.is_company,
                    'street': customer.street,
                    'city': customer.city,
                    'country': self._safe_field_value(customer, 'country_id'),
                    'vat': customer.vat,
                    'customer_rank': customer.customer_rank,
                })
            
            return self._format_response(
                success=True,
                data={
                    'customers': customers_data,
                    'count': len(customers_data),
                    'total_available': Partner.search_count(domain)
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to query customers: {str(e)}'
            )
