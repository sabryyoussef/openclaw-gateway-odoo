# API Endpoints Documentation

## Authentication
All requests require the `X-OPENCLAW-TOKEN` header.

## Available Skills
- `create_lead`: Create CRM leads
- `customers`: Retrieve customer data  
- `sales`: Sales order operations
- `summary`: Database statistics

## Example Usage
```bash
curl -X POST http://your-odoo-instance.com/api/skills/create_lead \
  -H "X-OPENCLAW-TOKEN: your-token" \
  -H "Content-Type: application/json" \
  -d '{"name": "Lead Name", "email_from": "lead@email.com"}'
```
