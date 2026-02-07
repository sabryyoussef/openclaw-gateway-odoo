# -*- coding: utf-8 -*-
"""Advanced Lead Executor - validation, duplicate check, optional assignment."""
from .base import BaseExecutor
import logging
import re

_logger = logging.getLogger(__name__)


class AdvancedLeadExecutor(BaseExecutor):
    """Advanced lead creation with validation and duplicate check."""

    def execute(self, env, payload):
        """
        Create lead with validation and optional duplicate check.

        Payload: name (required), contact_name, email_from, phone, company, website,
                 description, source, priority (low|medium|high), allow_duplicates.
        """
        if not payload.get('name'):
            return self._format_response(False, error='NAME_REQUIRED', message='Field "name" is required')

        try:
            lead_data = self._validate_lead_data(payload)
            if 'error' in lead_data:
                return self._format_response(False, error=lead_data['error'], message=lead_data.get('message'))

            duplicate = self._check_duplicate(env, lead_data)
            if duplicate and not payload.get('allow_duplicates', False):
                return self._format_response(
                    False,
                    error='DUPLICATE_FOUND',
                    message=f"Lead with email {lead_data.get('email_from', '')} already exists",
                    duplicate_id=duplicate.id
                )

            lead = env['crm.lead'].sudo().create(lead_data)
            result = {
                'lead_id': lead.id,
                'name': lead.name,
                'stage': lead.stage_id.name if lead.stage_id else 'New',
                'assigned_to': lead.user_id.name if lead.user_id else None,
                'team': lead.team_id.name if lead.team_id else None,
                'probability': lead.probability,
            }
            return self._format_response(True, data=result)
        except Exception as e:
            _logger.exception("Advanced lead creation error: %s", e)
            return self._format_response(False, error='CREATION_ERROR', message=str(e))

    def _validate_lead_data(self, payload):
        """Validate and sanitize lead data; return dict with error key if invalid."""
        name = payload.get('name')
        if not name or not str(name).strip():
            return {'error': 'NAME_REQUIRED', 'message': 'Name is required'}
        lead_data = {'name': str(name).strip(), 'type': 'opportunity'}

        if payload.get('contact_name'):
            lead_data['contact_name'] = str(payload['contact_name']).strip()
        if payload.get('partner_name'):
            lead_data['partner_name'] = str(payload['partner_name']).strip()

        email = payload.get('email_from')
        if email:
            email = str(email).strip().lower()
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                return {'error': 'INVALID_EMAIL', 'message': 'Invalid email format'}
            lead_data['email_from'] = email

        phone = payload.get('phone')
        if phone:
            lead_data['phone'] = re.sub(r'[^\d+\-()\s]', '', str(phone))

        for field in ('description', 'website'):
            if payload.get(field):
                lead_data[field] = str(payload[field]).strip()
        if payload.get('company'):
            lead_data['partner_name'] = lead_data.get('partner_name') or str(payload['company']).strip()

        priority_map = {'low': '1', 'medium': '2', 'high': '3'}
        if payload.get('priority'):
            lead_data['priority'] = priority_map.get(str(payload['priority']).lower(), '2')

        if payload.get('user_id'):
            try:
                lead_data['user_id'] = int(payload['user_id'])
            except (TypeError, ValueError):
                pass
        if payload.get('team_id'):
            try:
                lead_data['team_id'] = int(payload['team_id'])
            except (TypeError, ValueError):
                pass

        return lead_data

    def _check_duplicate(self, env, lead_data):
        """Return existing lead if same email_from exists, else None."""
        email = lead_data.get('email_from')
        if not email:
            return None
        return env['crm.lead'].sudo().search([('email_from', '=', email)], limit=1) or None
