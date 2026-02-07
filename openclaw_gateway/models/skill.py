# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json
import logging

# Import executor classes
from ..executors.ping import PingExecutor
from ..executors.sales import SalesOrdersExecutor
from ..executors.invoices import InvoicesExecutor
from ..executors.customers import CustomersExecutor
from ..executors.employees import EmployeesExecutor
from ..executors.products import ProductsExecutor
from ..executors.users import UsersExecutor
from ..executors.lead_creator import LeadCreatorExecutor
from ..executors.summary import SummaryExecutor
from ..executors.bulk_import import BulkImportExecutor
from ..executors.advanced_lead import AdvancedLeadExecutor

_logger = logging.getLogger(__name__)


class OpenClawSkill(models.Model):
    _name = "openclaw.skill"
    _description = "OpenClaw API Skill"
    _order = "sequence, name"

    name = fields.Char(string="Skill Name", required=True)
    code = fields.Char(
        string="Skill Code",
        required=True,
        index=True,
        help="URL-safe identifier (e.g., 'sales', 'ping', 'create_lead')"
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    description = fields.Text(string="Description")
    input_schema_json = fields.Text(
        string="Input Schema (JSON)",
        default="{}",
        help="JSON schema describing expected input payload"
    )
    output_schema_json = fields.Text(
        string="Output Schema (JSON)",
        default="{}",
        help="JSON schema describing output response format"
    )
    executor = fields.Selection(
        selection=[
            ('ping', 'Ping - Health Check'),
            ('sales_orders', 'Sales Orders - Query sale.order'),
            ('invoices', 'Invoices - Query account.move'),
            ('customers', 'Customers - Query res.partner'),
            ('employees', 'Employees - Query hr.employee'),
            ('products', 'Products - Query product.product'),
            ('users', 'Users - Query res.users'),
            ('create_lead', 'Create Lead - Create crm.lead'),
            ('summary', 'Summary - Database Statistics'),
            ('bulk_import', 'Bulk Import - Customers, Products, Leads'),
            ('advanced_lead', 'Advanced Lead - Create with validation'),
        ],
        string="Executor",
        required=True,
        help="Backend executor that handles this skill"
    )
    allowed_roles = fields.Many2many(
        'res.groups',
        'openclaw_skill_group_rel',
        'skill_id',
        'group_id',
        string="Allowed Roles",
        help="Which user groups can execute this skill"
    )
    max_limit = fields.Integer(
        string="Max Limit",
        default=100,
        help="Maximum number of records that can be returned per query"
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Skill code must be unique!')
    ]

    def run_skill(self, skill_code, payload, user_roles=None):
        """
        Execute a skill by code with given payload and user roles.
        
        Args:
            skill_code (str): Skill code identifier
            payload (dict): Input data for skill execution
            user_roles (list): List of user group IDs or group objects
            
        Returns:
            dict: Standardized response with success, data, error fields
        """
        # Find skill by code
        skill = self.sudo().search([('code', '=', skill_code), ('active', '=', True)], limit=1)
        
        if not skill:
            return {
                'success': False,
                'error': 'SKILL_NOT_FOUND',
                'message': f'Skill with code "{skill_code}" not found or inactive'
            }
        
        # Check role permissions if user_roles provided
        if user_roles and skill.allowed_roles:
            # Convert user_roles to IDs if they're recordsets
            role_ids = [r.id if hasattr(r, 'id') else r for r in user_roles]
            allowed_role_ids = skill.allowed_roles.ids
            
            # Check if user has at least one allowed role
            has_permission = any(role_id in allowed_role_ids for role_id in role_ids)
            
            if not has_permission:
                return {
                    'success': False,
                    'error': 'PERMISSION_DENIED',
                    'message': f'You do not have permission to execute skill "{skill_code}"',
                    'required_roles': skill.allowed_roles.mapped('name')
                }
        
        # Validate payload limit doesn't exceed max_limit
        limit = payload.get('limit', 10)
        if limit > skill.max_limit:
            return {
                'success': False,
                'error': 'LIMIT_EXCEEDED',
                'message': f'Requested limit {limit} exceeds maximum allowed {skill.max_limit}'
            }
        
        # Route to appropriate executor
        try:
            import time
            start_time = time.time()
            
            result = self._execute_skill(skill, payload)
            
            # Add query time
            duration_ms = int((time.time() - start_time) * 1000)
            result['query_time_ms'] = duration_ms
            result['skill'] = skill_code
            
            return result
            
        except Exception as e:
            _logger.exception(f"Error executing skill {skill_code}: {str(e)}")
            return {
                'success': False,
                'error': 'EXECUTION_ERROR',
                'message': f'Error executing skill: {str(e)}',
                'skill': skill_code
            }
    
    def _execute_skill(self, skill, payload):
        """
        Internal method to route skill execution to appropriate executor.
        """
        executor_type = skill.executor
        
        # Map executor types to executor classes
        executor_map = {
            'ping': PingExecutor,
            'sales_orders': SalesOrdersExecutor,
            'invoices': InvoicesExecutor,
            'customers': CustomersExecutor,
            'employees': EmployeesExecutor,
            'products': ProductsExecutor,
            'users': UsersExecutor,
            'create_lead': LeadCreatorExecutor,
            'summary': SummaryExecutor,
            'bulk_import': BulkImportExecutor,
            'advanced_lead': AdvancedLeadExecutor,
        }
        
        # Get executor class
        executor_class = executor_map.get(executor_type)
        
        if not executor_class:
            return {
                'success': False,
                'error': 'EXECUTOR_NOT_FOUND',
                'message': f'Executor "{executor_type}" is not implemented'
            }
        
        # Instantiate and execute
        executor = executor_class()
        return executor.execute(self.env, payload)
