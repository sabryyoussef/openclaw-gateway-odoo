# -*- coding: utf-8 -*-
"""Employees Executor"""
from .base import BaseExecutor


class EmployeesExecutor(BaseExecutor):
    """Executor for querying employees"""
    
    def execute(self, env, payload):
        """
        Query employees.
        
        Args:
            env: Odoo environment
            payload (dict): {
                'limit': int (optional, default 10),
                'department_id': int (optional, filter by department),
                'active': bool (optional, filter active/inactive)
            }
            
        Returns:
            dict: {'success': True, 'data': {'employees': [...], 'count': int}}
        """
        limit = self._validate_limit(payload.get('limit'), 100)
        
        # Build domain
        domain = []
        if payload.get('department_id'):
            domain.append(('department_id', '=', int(payload['department_id'])))
        if payload.get('active') is not None:
            domain.append(('active', '=', bool(payload['active'])))
        
        try:
            # Query employees
            Employee = env['hr.employee'].sudo()
            employees = Employee.search(domain, limit=limit, order='name asc')
            
            # Format results
            employees_data = []
            for employee in employees:
                employees_data.append({
                    'id': employee.id,
                    'name': employee.name,
                    'work_email': employee.work_email,
                    'work_phone': employee.work_phone,
                    'mobile_phone': employee.mobile_phone,
                    'job_title': employee.job_title,
                    'department': self._safe_field_value(employee, 'department_id'),
                    'manager': self._safe_field_value(employee, 'parent_id'),
                    'active': employee.active,
                })
            
            return self._format_response(
                success=True,
                data={
                    'employees': employees_data,
                    'count': len(employees_data),
                    'total_available': Employee.search_count(domain)
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='QUERY_ERROR',
                message=f'Failed to query employees: {str(e)}'
            )
