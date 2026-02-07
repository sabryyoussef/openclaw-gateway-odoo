# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


class OpenClawWebhookLog(models.Model):
    _name = 'openclaw.webhook.log'
    _description = 'Webhook Call Log'
    _order = 'create_date desc'

    webhook_id = fields.Char('Webhook ID', required=True, index=True)
    payload_json = fields.Text('Request Payload')
    response_json = fields.Text('Response Data')
    status_code = fields.Integer('HTTP Status', default=200)
    execution_time_ms = fields.Float('Execution Time (ms)')
    source_ip = fields.Char('Source IP')
    n8n_workflow_id = fields.Char('N8N Workflow ID')
    success = fields.Boolean('Success', default=True)
    error_message = fields.Text('Error Message')

    @api.model
    def log_webhook(self, webhook_id, payload, response, status_code=200,
                    execution_time_ms=0, source_ip=None, workflow_id=None):
        """Log webhook execution (optional helper for external callers)."""
        return self.create({
            'webhook_id': webhook_id,
            'payload_json': json.dumps(payload) if payload else None,
            'response_json': json.dumps(response) if response else None,
            'status_code': status_code,
            'execution_time_ms': execution_time_ms,
            'source_ip': source_ip,
            'n8n_workflow_id': workflow_id,
            'success': status_code < 400,
            'error_message': response.get('error') if isinstance(response, dict) else None,
        })


class OpenClawWorkflowJob(models.Model):
    _name = 'openclaw.workflow.job'
    _description = 'N8N Workflow Job Status'
    _order = 'create_date desc'

    job_id = fields.Char('Job ID', required=True, index=True)
    workflow_type = fields.Selection([
        ('bulk_import', 'Bulk Import'),
        ('lead_creation', 'Lead Creation'),
        ('data_sync', 'Data Synchronization'),
        ('report_generation', 'Report Generation'),
    ], required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], default='pending', required=True)
    progress_percent = fields.Float('Progress %', default=0.0)
    result_json = fields.Text('Result Data')
    error_message = fields.Text('Error Message')
    n8n_execution_id = fields.Char('N8N Execution ID')
    estimated_completion = fields.Datetime('Estimated Completion')
