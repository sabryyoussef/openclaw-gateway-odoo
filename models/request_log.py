# -*- coding: utf-8 -*-
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class OpenClawRequestLog(models.Model):
    _name = "openclaw.request.log"
    _description = "OpenClaw API Request Log"
    _order = "create_date desc"
    _rec_name = "endpoint"

    token_name = fields.Char(
        string="Token Name",
        help="Name/identifier of the token used"
    )
    endpoint = fields.Char(
        string="Endpoint",
        help="API endpoint accessed (e.g., '/api/skills/sales')"
    )
    method = fields.Char(
        string="HTTP Method",
        help="HTTP method used (GET, POST, etc.)"
    )
    skill_code = fields.Char(
        string="Skill Code",
        index=True,
        help="Skill that was executed (if applicable)"
    )
    request_json = fields.Text(
        string="Request Payload",
        help="JSON payload sent in the request"
    )
    response_json = fields.Text(
        string="Response Data",
        help="JSON response returned to client"
    )
    status = fields.Selection(
        [
            ('ok', 'OK'),
            ('error', 'Error'),
        ],
        string="Status",
        index=True,
        help="Whether request succeeded or failed"
    )
    error = fields.Char(
        string="Error Code",
        help="Error code if request failed"
    )
    duration_ms = fields.Integer(
        string="Duration (ms)",
        help="Request processing time in milliseconds"
    )
    remote_addr = fields.Char(
        string="Remote IP",
        help="IP address of the client"
    )
    user_agent = fields.Char(
        string="User Agent",
        help="Client user agent string"
    )
    
    # Timestamps (automatic)
    create_date = fields.Datetime(string="Created At", readonly=True)
    create_uid = fields.Many2one('res.users', string="Created By", readonly=True)

    def action_view_raw_json(self):
        """Button action: raw JSON is shown in the Request/Response notebook pages."""
        return True

    @staticmethod
    def safe_log_request(env, token_name, endpoint, method, skill_code, request_data, 
                        response_data, duration_ms, status, error=None, 
                        remote_addr=None, user_agent=None):
        """
        Safely create a request log entry without breaking API flow if logging fails.
        
        Args:
            env: Odoo environment
            token_name (str): Token identifier
            endpoint (str): API endpoint path
            method (str): HTTP method
            skill_code (str): Skill code executed
            request_data (dict): Request payload
            response_data (dict): Response data
            duration_ms (int): Processing duration
            status (str): 'ok' or 'error'
            error (str, optional): Error code if failed
            remote_addr (str, optional): Client IP
            user_agent (str, optional): Client user agent
        """
        try:
            import json
            
            env['openclaw.request.log'].sudo().create({
                'token_name': token_name,
                'endpoint': endpoint,
                'method': method,
                'skill_code': skill_code,
                'request_json': json.dumps(request_data) if request_data else '{}',
                'response_json': json.dumps(response_data) if response_data else '{}',
                'status': status,
                'error': error,
                'duration_ms': duration_ms,
                'remote_addr': remote_addr,
                'user_agent': user_agent,
            })
        except Exception as e:
            # Log the error but don't break the API
            _logger.error(f"Failed to log API request: {str(e)}")
