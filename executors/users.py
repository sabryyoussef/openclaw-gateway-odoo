# -*- coding: utf-8 -*-
"""Users Executor"""
from .base import BaseExecutor


class UsersExecutor(BaseExecutor):
    """Executor for querying users"""
    
    def execute(self, env, payload):
        """
        Query users.
        
        Args:
            env: Odoo environment
            payload (dict): {
                'limit': int (optional, default 10),
                'active': bool (optional, filter active/inactive)
            }
            
        Returns:
            dict: {'success': True, 'data': {'users': [...], 'count': int}}
        """
        limit = self._validate_limit(payload.get('limit'), 100)
        
        # Build domain
        domain = []
        if payload.get('active') is not None:
            domain.append(('active', '=', bool(payload['active'])))
        
        try:
            # Query users
            User = env['res.users'].sudo()
            users = User.search(domain, limit=limit, order='name asc')
            
            # Format results
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email,
                    'active': user.active,
                    'company': self._safe_field_value(user, 'company_id'),
                    'lang': user.lang,
                    'tz': user.tz,
                })
            
            return self._format_response(
                success=True,
                data={
                    'users': users_data,
                    'count': len(users_data),
                    'total_available': User.search_count(domain)
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to query users: {str(e)}'
            )
