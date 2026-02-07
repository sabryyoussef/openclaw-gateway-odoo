# -*- coding: utf-8 -*-
"""Ping Executor - Health Check"""
from datetime import datetime
from .base import BaseExecutor


class PingExecutor(BaseExecutor):
    """Simple health check executor"""
    
    def execute(self, env, payload):
        """
        Return pong with current timestamp.
        
        Args:
            env: Odoo environment
            payload (dict): Not used
            
        Returns:
            dict: {'success': True, 'data': {'message': 'pong', 'timestamp': ...}}
        """
        return self._format_response(
            success=True,
            data={
                'message': 'pong',
                'timestamp': datetime.now().isoformat(),
                'version': '18.0.1.0.0'
            }
        )
