# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import hmac
import hashlib
import logging
import time

_logger = logging.getLogger(__name__)


class OpenClawWebhookController(http.Controller):

    @http.route('/webhook/n8n/<string:webhook_id>', type='http',
                auth='none', methods=['POST'], csrf=False)
    def n8n_webhook(self, webhook_id, **kwargs):
        """Handle incoming webhooks from N8N workflows"""
        start = time.time()
        source_ip = request.httprequest.remote_addr
        data = request.httprequest.get_data(as_text=True)
        headers = dict(request.httprequest.headers)

        if not self._validate_webhook_signature(data, headers, webhook_id):
            response = self._webhook_response({
                'success': False,
                'error': 'INVALID_SIGNATURE'
            }, status=401)
            self._log_webhook(webhook_id, data, {'success': False, 'error': 'INVALID_SIGNATURE'},
                              401, (time.time() - start) * 1000, source_ip, None)
            return response

        try:
            payload = json.loads(data) if data else {}

            if webhook_id == 'lead_created':
                result = self._handle_lead_created_webhook(payload)
            elif webhook_id == 'bulk_import_complete':
                result = self._handle_bulk_import_webhook(payload)
            elif webhook_id == 'workflow_status':
                result = self._handle_workflow_status_webhook(payload)
            else:
                raise ValueError(f"Unknown webhook ID: {webhook_id}")

            elapsed_ms = (time.time() - start) * 1000
            self._log_webhook(webhook_id, payload, result, 200, elapsed_ms, source_ip,
                              payload.get('n8n_workflow_id') or payload.get('workflow_id'))
            return self._webhook_response(result, status=200)

        except Exception as e:
            _logger.error("Webhook error for %s: %s", webhook_id, str(e))
            err_payload = {'success': False, 'error': 'WEBHOOK_ERROR', 'message': str(e)}
            elapsed_ms = (time.time() - start) * 1000
            self._log_webhook(webhook_id, data if isinstance(data, str) else {},
                              err_payload, 500, elapsed_ms, source_ip, None)
            return self._webhook_response(err_payload, status=500)

    def _validate_webhook_signature(self, data, headers, webhook_id):
        """Validate webhook signature from N8N"""
        webhook_secret = request.env['ir.config_parameter'].sudo().get_param(
            'openclaw_gateway.webhook_secret'
        )
        if not webhook_secret:
            _logger.warning("No webhook secret configured")
            return True
        signature = headers.get('X-OpenClaw-Signature')
        if not signature:
            return False
        expected = hmac.new(
            webhook_secret.encode(),
            data.encode() if data else b'',
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    def _webhook_response(self, data, status=200):
        """Format webhook response"""
        response = request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )
        response.status_code = status
        return response

    def _log_webhook(self, webhook_id, payload, response, status_code, execution_time_ms,
                     source_ip, workflow_id):
        """Log webhook execution via openclaw.webhook.log"""
        try:
            payload_json = json.dumps(payload) if not isinstance(payload, str) else payload
            response_json = json.dumps(response) if isinstance(response, dict) else str(response)
            request.env['openclaw.webhook.log'].sudo().create({
                'webhook_id': webhook_id,
                'payload_json': payload_json,
                'response_json': response_json,
                'status_code': status_code,
                'execution_time_ms': execution_time_ms,
                'source_ip': source_ip,
                'n8n_workflow_id': workflow_id,
                'success': status_code < 400,
                'error_message': response.get('error') if isinstance(response, dict) else None,
            })
        except Exception as e:
            _logger.warning("Could not write webhook log: %s", e)

    def _handle_lead_created_webhook(self, payload):
        """Acknowledge lead creation callback from N8N."""
        return {
            'success': True,
            'webhook': 'lead_created',
            'message': 'Lead creation acknowledged',
            'lead_id': payload.get('lead_id'),
        }

    def _handle_bulk_import_webhook(self, payload):
        """Acknowledge bulk import completion from N8N."""
        job_id = payload.get('job_id')
        if job_id:
            job = request.env['openclaw.workflow.job'].sudo().search(
                [('job_id', '=', job_id)], limit=1
            )
            if job:
                job.write({
                    'status': 'completed',
                    'progress_percent': 100.0,
                    'result_json': json.dumps(payload.get('result', payload)),
                })
        return {
            'success': True,
            'webhook': 'bulk_import_complete',
            'message': 'Bulk import acknowledged',
            'job_id': job_id,
        }

    def _handle_workflow_status_webhook(self, payload):
        """Update workflow job status from N8N."""
        job_id = payload.get('job_id') or payload.get('n8n_execution_id')
        status = payload.get('status')
        if job_id and status:
            job = request.env['openclaw.workflow.job'].sudo().search(
                [('job_id', '=', job_id)], limit=1
            )
            if not job and status in ('pending', 'running'):
                job = request.env['openclaw.workflow.job'].sudo().create({
                    'job_id': job_id,
                    'workflow_type': payload.get('workflow_type', 'data_sync'),
                    'status': status,
                    'progress_percent': payload.get('progress_percent', 0.0),
                    'n8n_execution_id': payload.get('n8n_execution_id'),
                    'error_message': payload.get('error_message'),
                })
            elif job:
                job.write({
                    'status': status,
                    'progress_percent': payload.get('progress_percent', job.progress_percent),
                    'result_json': json.dumps(payload.get('result')) if payload.get('result') else job.result_json,
                    'error_message': payload.get('error_message') or job.error_message,
                })
        return {
            'success': True,
            'webhook': 'workflow_status',
            'message': 'Status updated',
            'job_id': job_id,
        }
