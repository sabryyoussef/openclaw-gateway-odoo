# -*- coding: utf-8 -*-
"""Lead Creator Executor"""
from .base import BaseExecutor


class LeadCreatorExecutor(BaseExecutor):
    """Executor for creating CRM leads"""
    
    def execute(self, env, payload):
        """
        Create a new CRM lead.
        
        Args:
            env: Odoo environment
            payload (dict): {
                'name': str (required, lead title),
                'partner_name': str (optional, customer name),
                'email_from': str (optional, customer email),
                'phone': str (optional, customer phone),
                'description': str (optional, lead notes),
                'user_id': int (optional, assigned salesperson),
                'team_id': int (optional, sales team)
            }
            
        Returns:
            dict: {'success': True, 'data': {'lead_id': int, 'name': str}}
        """
        # Validate required fields
        if not payload.get('name'):
            return self._format_response(
                success=False,
                error='MISSING_FIELD',
                message='Field "name" is required'
            )
        
        try:
            # Prepare lead data
            lead_data = {
                'name': payload['name'],
                'type': 'opportunity',
            }
            
            # Add optional fields
            if payload.get('partner_name'):
                lead_data['partner_name'] = payload['partner_name']
            if payload.get('email_from'):
                lead_data['email_from'] = payload['email_from']
            if payload.get('phone'):
                lead_data['phone'] = payload['phone']
            if payload.get('description'):
                lead_data['description'] = payload['description']
            if payload.get('user_id'):
                lead_data['user_id'] = int(payload['user_id'])
            if payload.get('team_id'):
                lead_data['team_id'] = int(payload['team_id'])
            
            # Create lead
            Lead = env['crm.lead'].sudo()
            lead = Lead.create(lead_data)
            
            return self._format_response(
                success=True,
                data={
                    'lead_id': lead.id,
                    'name': lead.name,
                    'stage': self._safe_field_value(lead, 'stage_id'),
                }
            )
            
        except Exception as e:
            return self._format_response(
                success=False,
                error='CREATE_ERROR',
                message=f'Failed to create lead: {str(e)}'
            )
