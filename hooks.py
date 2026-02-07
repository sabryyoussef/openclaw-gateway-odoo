# -*- coding: utf-8 -*-
"""Module hooks: create access rights, actions and menus for webhook models after upgrade."""


def post_init_hook(cr, registry):
    """Create access rights, actions and menus for openclaw.webhook.log and openclaw.workflow.job."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    IrModel = env['ir.model']
    webhook_log_model = IrModel.search([('model', '=', 'openclaw.webhook.log')], limit=1)
    workflow_job_model = IrModel.search([('model', '=', 'openclaw.workflow.job')], limit=1)
    if not webhook_log_model or not workflow_job_model:
        return

    group_admin = env.ref('openclaw_gateway.group_openclaw_api_admin')
    group_user = env.ref('base.group_user')
    IrModelAccess = env['ir.model.access']

    # Access rights
    access_list = [
        ('openclaw.webhook.log admin', webhook_log_model.id, group_admin.id, 1, 1, 1, 1),
        ('openclaw.webhook.log user', webhook_log_model.id, group_user.id, 1, 0, 0, 0),
        ('openclaw.workflow.job admin', workflow_job_model.id, group_admin.id, 1, 1, 1, 1),
        ('openclaw.workflow.job user', workflow_job_model.id, group_user.id, 1, 0, 0, 0),
    ]
    for name, model_id, group_id, r, w, c, u in access_list:
        if not IrModelAccess.search([('name', '=', name)], limit=1):
            IrModelAccess.create({
                'name': name,
                'model_id': model_id,
                'group_id': group_id,
                'perm_read': r,
                'perm_write': w,
                'perm_create': c,
                'perm_unlink': u,
            })

    # Actions and menus (so they exist even when XML actions are not loaded)
    ActWindow = env['ir.actions.act_window']
    Menu = env['ir.ui.menu']
    menu_monitoring = env.ref('openclaw_gateway.menu_openclaw_monitoring', raise_if_not_found=False)
    if not menu_monitoring:
        return

    # Webhook Logs action + menu
    action_webhook_log = ActWindow.search([
        ('res_model', '=', 'openclaw.webhook.log'),
        ('binding_model_id', '=', False),
    ], limit=1)
    if not action_webhook_log:
        action_webhook_log = ActWindow.create({
            'name': 'Webhook Logs',
            'res_model': 'openclaw.webhook.log',
            'view_mode': 'list,form',
            'help': '<p class="o_view_nocontent_empty_folder">No webhook calls logged yet</p><p>Webhook logs appear here when N8N calls /webhook/n8n/&lt;webhook_id&gt;.</p>',
        })
    if not Menu.search([('name', '=', 'Webhook Logs'), ('parent_id', '=', menu_monitoring.id)], limit=1):
        Menu.create({
            'name': 'Webhook Logs',
            'parent_id': menu_monitoring.id,
            'action': 'ir.actions.act_window,%d' % action_webhook_log.id,
            'sequence': 20,
            'groups_id': [(6, 0, [group_admin.id, group_user.id])],
        })

    # Workflow Jobs action + menu
    action_workflow_job = ActWindow.search([
        ('res_model', '=', 'openclaw.workflow.job'),
        ('binding_model_id', '=', False),
    ], limit=1)
    if not action_workflow_job:
        action_workflow_job = ActWindow.create({
            'name': 'Workflow Jobs',
            'res_model': 'openclaw.workflow.job',
            'view_mode': 'list,form',
            'help': '<p class="o_view_nocontent_empty_folder">No workflow jobs yet</p><p>Jobs are created when N8N sends workflow_status webhooks or when bulk operations run.</p>',
        })
    if not Menu.search([('name', '=', 'Workflow Jobs'), ('parent_id', '=', menu_monitoring.id)], limit=1):
        Menu.create({
            'name': 'Workflow Jobs',
            'parent_id': menu_monitoring.id,
            'action': 'ir.actions.act_window,%d' % action_workflow_job.id,
            'sequence': 30,
            'groups_id': [(6, 0, [group_admin.id, group_user.id])],
        })

    # Create bulk_import and advanced_lead skills if executor options exist (new code deployed)
    try:
        Skill = env['openclaw.skill'].sudo()
        if not Skill.search([('code', '=', 'bulk_import')], limit=1):
            Skill.create({
                'name': 'Bulk Import',
                'code': 'bulk_import',
                'sequence': 95,
                'active': True,
                'description': 'Bulk import records for customers (res.partner), products (product.template), or leads (crm.lead). Payload: type (customers|products|leads), data (list of dicts), validate_only, batch_size (default 50, max 500), update_existing.',
                'executor': 'bulk_import',
                'max_limit': 500,
                'input_schema_json': '{"type": "string (required: customers|products|leads)", "data": "array of records (required)", "validate_only": "bool", "batch_size": "int (1-500)", "update_existing": "bool"}',
                'output_schema_json': '{"total_records": "int", "processed": "int", "created": "int", "updated": "int", "skipped": "int", "errors": "array"}',
            })
        if not Skill.search([('code', '=', 'advanced_lead')], limit=1):
            Skill.create({
                'name': 'Advanced Lead',
                'code': 'advanced_lead',
                'sequence': 96,
                'active': True,
                'description': 'Create a CRM lead with validation (email format, duplicate check). Payload: name (required), email_from, phone, partner_name, description, priority (low|medium|high), allow_duplicates.',
                'executor': 'advanced_lead',
                'max_limit': 1,
                'input_schema_json': '{"name": "string (required)", "email_from": "string", "phone": "string", "partner_name": "string", "description": "string", "priority": "low|medium|high", "allow_duplicates": "bool"}',
                'output_schema_json': '{"lead_id": "int", "name": "string", "stage": "string", "assigned_to": "string", "team": "string", "probability": "float"}',
            })
    except (ValueError, KeyError):
        # Old code: executor selection does not include bulk_import/advanced_lead; skip
        pass
