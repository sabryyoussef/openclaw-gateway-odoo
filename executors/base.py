# -*- coding: utf-8 -*-
"""Base Executor Class for OpenClaw Skills"""
import logging

_logger = logging.getLogger(__name__)


class BaseExecutor:
    """
    Base class for skill executors.
    All executors should inherit from this class.
    """
    
    def execute(self, env, payload):
        """
        Execute the skill with given payload.
        
        Args:
            env: Odoo environment
            payload (dict): Input data for skill execution
            
        Returns:
            dict: Standardized response {'success': bool, 'data': ..., 'error': ...}
        """
        raise NotImplementedError("Subclasses must implement execute() method")
    
    def _validate_limit(self, limit, max_limit):
        """
        Validate and sanitize limit parameter.
        
        Args:
            limit (int): Requested limit
            max_limit (int): Maximum allowed limit
            
        Returns:
            int: Validated limit value
        """
        try:
            limit = int(limit) if limit else 10
        except (ValueError, TypeError):
            limit = 10
        
        # Ensure limit is positive and doesn't exceed max
        limit = max(1, min(limit, max_limit))
        return limit
    
    def _format_response(self, success, data=None, error=None, message=None):
        """
        Format standardized response.
        
        Args:
            success (bool): Whether operation succeeded
            data: Response data
            error (str): Error code if failed
            message (str): Human-readable message
            
        Returns:
            dict: Standardized response
        """
        response = {'success': success}
        
        if success:
            if data is not None:
                response['data'] = data
        else:
            if error:
                response['error'] = error
            if message:
                response['message'] = message
        
        return response
    
    def _safe_field_value(self, record, field_name):
        """
        Safely extract field value from record, handling Many2one fields.
        
        Args:
            record: Odoo record
            field_name (str): Field name
            
        Returns:
            Field value (str for Many2one, original type for others)
        """
        try:
            value = record[field_name]
            # Handle Many2one fields - return name instead of tuple
            if hasattr(value, 'name'):
                return value.name
            return value
        except (KeyError, AttributeError):
            return None
    
    def _format_date(self, date_value):
        """
        Format date/datetime to ISO string.
        
        Args:
            date_value: Date or datetime object
            
        Returns:
            str: ISO formatted date string or None
        """
        if not date_value:
            return None
        try:
            return date_value.isoformat()
        except (AttributeError, ValueError):
            return str(date_value)
