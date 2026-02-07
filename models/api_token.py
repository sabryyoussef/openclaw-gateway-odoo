# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class OpenClawAPIToken(models.Model):
    _name = "openclaw.api.token"
    _description = "OpenClaw API Token"
    _order = "name"

    name = fields.Char(
        string="Token Name",
        required=True,
        help="Identifier/label for this token (e.g., 'Production Token', 'n8n Integration')"
    )
    token = fields.Char(
        string="Token Value",
        required=True,
        index=True,
        help="The actual token string used in X-OPENCLAW-TOKEN header"
    )
    active = fields.Boolean(string="Active", default=True)
    allowed_skills = fields.Many2many(
        'openclaw.skill',
        'openclaw_token_skill_rel',
        'token_id',
        'skill_id',
        string="Allowed Skills",
        help="Skills this token can execute. Leave empty to allow all skills."
    )
    allowed_ip_addresses = fields.Text(
        string="Allowed IP Addresses",
        help="Comma-separated list of allowed IP addresses. Leave empty to allow all IPs."
    )
    user_roles = fields.Many2many(
        'res.groups',
        'openclaw_token_group_rel',
        'token_id',
        'group_id',
        string="User Roles",
        help="Permissions/roles this token has (Admin, Sales, HR, Finance)"
    )
    expiry_date = fields.Datetime(
        string="Expiry Date",
        help="Optional expiration date for this token"
    )
    last_used_date = fields.Datetime(
        string="Last Used",
        readonly=True,
        help="Timestamp of last API request using this token"
    )
    use_count = fields.Integer(
        string="Use Count",
        readonly=True,
        default=0,
        help="Number of times this token has been used"
    )

    _sql_constraints = [
        ('token_unique', 'UNIQUE(token)', 'Token value must be unique!')
    ]

    def validate_token(self, token_value, skill_code=None, remote_addr=None):
        """
        Validate an API token and check permissions.
        
        Args:
            token_value (str): The token string to validate
            skill_code (str, optional): Skill code to check permission for
            remote_addr (str, optional): Remote IP address to validate
            
        Returns:
            dict: {
                'valid': True/False,
                'token_record': token record if valid,
                'roles': list of group records,
                'error': error code if invalid,
                'message': error message if invalid
            }
        """
        # Find token
        token_rec = self.sudo().search([('token', '=', token_value)], limit=1)
        
        if not token_rec:
            return {
                'valid': False,
                'error': 'INVALID_TOKEN',
                'message': 'Token not found'
            }
        
        # Check if active
        if not token_rec.active:
            return {
                'valid': False,
                'error': 'TOKEN_INACTIVE',
                'message': 'Token is inactive'
            }
        
        # Check expiry
        if token_rec.expiry_date:
            if fields.Datetime.now() > token_rec.expiry_date:
                return {
                    'valid': False,
                    'error': 'TOKEN_EXPIRED',
                    'message': f'Token expired on {token_rec.expiry_date}'
                }
        
        # Check IP whitelist
        if token_rec.allowed_ip_addresses and remote_addr:
            allowed_ips = [ip.strip() for ip in token_rec.allowed_ip_addresses.split(',')]
            if remote_addr not in allowed_ips:
                return {
                    'valid': False,
                    'error': 'IP_NOT_ALLOWED',
                    'message': f'IP address {remote_addr} is not in allowlist'
                }
        
        # Check skill permission
        if skill_code and token_rec.allowed_skills:
            skill = self.env['openclaw.skill'].sudo().search([('code', '=', skill_code)], limit=1)
            if skill and skill not in token_rec.allowed_skills:
                return {
                    'valid': False,
                    'error': 'SKILL_NOT_ALLOWED',
                    'message': f'Token does not have permission for skill "{skill_code}"'
                }
        
        # Token is valid
        return {
            'valid': True,
            'token_record': token_rec,
            'roles': token_rec.user_roles,
            'token_name': token_rec.name
        }
    
    def update_usage(self):
        """Update last_used_date and increment use_count"""
        self.ensure_one()
        self.sudo().write({
            'last_used_date': fields.Datetime.now(),
            'use_count': self.use_count + 1
        })
    
    @api.model
    def generate_token(self):
        """Generate a cryptographically secure random token"""
        import secrets
        return secrets.token_urlsafe(32)

    def action_generate_token(self):
        """Button action: generate a new token and set it on the current record(s)."""
        for rec in self:
            rec.token = self.generate_token()
        return True
