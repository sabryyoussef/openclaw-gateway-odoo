# -*- coding: utf-8 -*-
"""Products Executor"""
from .base import BaseExecutor


class ProductsExecutor(BaseExecutor):
    """Executor for querying products"""
    
    def execute(self, env, payload):
        """
        Query products.
        
        Args:
            env: Odoo environment
            payload (dict): {
                'limit': int (optional, default 10),
                'active': bool (optional, filter active/inactive),
                'sale_ok': bool (optional, filter products that can be sold),
                'search': str (optional, search in name/default_code)
            }
            
        Returns:
            dict: {'success': True, 'data': {'products': [...], 'count': int}}
        """
        limit = self._validate_limit(payload.get('limit'), 100)
        
        # Build domain
        domain = []
        if payload.get('active') is not None:
            domain.append(('active', '=', bool(payload['active'])))
        if payload.get('sale_ok') is not None:
            domain.append(('sale_ok', '=', bool(payload['sale_ok'])))
        if payload.get('search'):
            search_term = payload['search']
            domain.append('|')
            domain.append(('name', 'ilike', search_term))
            domain.append(('default_code', 'ilike', search_term))
        
        try:
            # Query products
            Product = env['product.product'].sudo()
            products = Product.search(domain, limit=limit, order='name asc')
            
            # Format results
            products_data = []
            for product in products:
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code,
                    'barcode': product.barcode,
                    'list_price': product.list_price,
                    'standard_price': product.standard_price,
                    'uom': self._safe_field_value(product, 'uom_id'),
                    'categ': self._safe_field_value(product, 'categ_id'),
                    'type': product.type,
                    'sale_ok': product.sale_ok,
                    'purchase_ok': product.purchase_ok,
                    'active': product.active,
                })
            
            return self._format_response(
                success=True,
                data={
                    'products': products_data,
                    'count': len(products_data),
                    'total_available': Product.search_count(domain)
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to query products: {str(e)}'
            )
