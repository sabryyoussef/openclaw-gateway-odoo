# Webhook Logs & Workflow Jobs menus not showing

The **Webhook Logs** and **Workflow Jobs** menus appear under **OpenClaw API → Monitoring** only if the webhook models are loaded. They are created by the module's post_init_hook when it finds the models.

## 1. Ensure these files exist on the server

On the server (e.g. `/opt/odoo/custom_addons/openclaw_gateway/`), you must have:

- `models/webhook_log.py` (defines `openclaw.webhook.log` and `openclaw.workflow.job`)
- `models/__init__.py` must contain: `from . import webhook_log`
- `hooks.py` (post_init_hook that creates access rights and menus)
- `__manifest__.py` must contain: `'post_init_hook': 'openclaw_gateway.hooks:post_init_hook'`

## 2. Restart Odoo and upgrade

1. Copy the full `openclaw_gateway` folder from your project to the server's addons path (replace the existing one).
2. **Restart Odoo** so Python reloads (e.g. `sudo systemctl restart odoo`).
3. In Odoo: **Apps** → find **OpenClaw Gateway** → **Upgrade**.
4. Open **OpenClaw API** → click **Monitoring**. You should see **Request Logs**, **Webhook Logs**, **Workflow Jobs**.

## 3. Your user must see the app

Your user has **OpenClaw API Admin** in Settings; that is enough. The new menus are visible to users with OpenClaw API Admin or Internal User.

If after a full deploy + restart + upgrade you still only see **Request Logs** under Monitoring, the hook did not find the models — double-check that `models/webhook_log.py` exists on the server and that `models/__init__.py` imports it.
