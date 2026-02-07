# -*- coding: utf-8 -*-
{
    'name': 'OpenClaw Gateway (API Skills)',
    'version': '18.0.1.2.0',
    'category': 'Tools',
    'summary': 'API Skills Gateway for OpenClaw and n8n Integration',
    'description': """
OpenClaw Gateway - API Skills System
=====================================

Exposes secure API endpoints for querying and managing Odoo data via OpenClaw, 
Telegram, WhatsApp, and n8n automations.

Features:
---------
* Multi-token authentication with role-based access control
* 9 production-ready skills (sales, invoices, customers, employees, products, users, create_lead, summary, ping)
* Request logging and audit trail
* IP whitelisting support
* Token expiry management
* Modular executor architecture
* WhatsApp/Telegram-friendly responses

API Endpoints:
--------------
* GET  /api/health - Health check (no auth)
* GET  /api/skills - List available skills
* POST /api/skills/<code> - Execute skill

Security:
---------
* Token-based authentication (X-OPENCLAW-TOKEN header)
* Per-token skill permissions
* Role-based access (Admin, Sales, HR, Finance)
* Optional IP whitelisting
* Token expiry support
* Full request/response logging

Integration:
-----------
Works with OpenClaw (Telegram/WhatsApp bot), n8n (automation), 
and any HTTP client supporting JSON APIs.
    """,
    'author': 'Freezoner',
    'website': 'https://freezoner.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_management',
        'account',
        'hr',
        'crm',
        'product',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/skill_views.xml',
        'views/api_token_views.xml',
        'views/request_log_views.xml',
        'views/webhook_views.xml',
        'views/menu.xml',
        'data/seed_skills.xml',
        'data/seed_tokens.xml',
        'data/n8n_config.xml',
    ],
    'external_dependencies': {
        'python': [],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'openclaw_gateway.hooks:post_init_hook',
}
