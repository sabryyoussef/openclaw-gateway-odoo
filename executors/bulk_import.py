# -*- coding: utf-8 -*-
"""Bulk Import Executor - customers, products, leads."""
from .base import BaseExecutor
import logging

_logger = logging.getLogger(__name__)


class BulkImportExecutor(BaseExecutor):
    """Handle bulk data import operations."""

    def execute(self, env, payload):
        """
        Execute bulk import operation.

        Args:
            payload (dict): {
                'type': 'customers|products|leads',
                'data': [list of records],
                'validate_only': bool,
                'batch_size': int,
                'update_existing': bool
            }
        """
        if not payload.get('type'):
            return self._format_response(False, error='TYPE_REQUIRED', message='Payload "type" is required')
        if not payload.get('data'):
            return self._format_response(False, error='DATA_REQUIRED', message='Payload "data" (list of records) is required')

        import_type = payload['type']
        data = payload['data']
        if not isinstance(data, list):
            return self._format_response(False, error='DATA_INVALID', message='"data" must be a list of records')
        validate_only = payload.get('validate_only', False)
        batch_size = max(1, min(int(payload.get('batch_size', 50)), 500))
        update_existing = payload.get('update_existing', False)

        try:
            if import_type == 'customers':
                result = self._import_customers(env, data, validate_only, batch_size, update_existing)
            elif import_type == 'products':
                result = self._import_products(env, data, validate_only, batch_size, update_existing)
            elif import_type == 'leads':
                result = self._import_leads(env, data, validate_only, batch_size, update_existing)
            else:
                return self._format_response(
                    False,
                    error='INVALID_TYPE',
                    message=f'type must be customers, products, or leads; got {import_type!r}'
                )
            return self._format_response(True, data=result)
        except Exception as e:
            _logger.exception("Bulk import error for type %s: %s", import_type, e)
            return self._format_response(False, error='IMPORT_ERROR', message=str(e))

    def _import_customers(self, env, data, validate_only, batch_size, update_existing):
        """Import customer records (res.partner with customer_rank)."""
        results = {
            'total_records': len(data),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }
        partner_model = env['res.partner'].sudo()
        for i, record in enumerate(data[:batch_size]):
            if not isinstance(record, dict):
                results['errors'].append({'line': i + 1, 'error': 'Record must be a dict'})
                continue
            try:
                if not record.get('name'):
                    results['errors'].append({'line': i + 1, 'error': 'Name is required'})
                    continue
                if validate_only:
                    results['processed'] += 1
                    continue
                existing = False
                if record.get('email'):
                    existing = partner_model.search([('email', '=', record['email'])], limit=1)
                vals = {k: v for k, v in record.items() if k in partner_model._fields}
                if 'customer_rank' not in vals:
                    vals['customer_rank'] = 1
                if existing and update_existing:
                    existing.write(vals)
                    results['updated'] += 1
                elif existing:
                    results['skipped'] += 1
                else:
                    partner_model.create(vals)
                    results['created'] += 1
                results['processed'] += 1
            except Exception as e:
                results['errors'].append({'line': i + 1, 'error': str(e)})
        return results

    def _import_products(self, env, data, validate_only, batch_size, update_existing):
        """Import product records (product.template)."""
        results = {
            'total_records': len(data),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }
        product_model = env['product.template'].sudo()
        # Fields we allow for product.template (avoid relation fields that need IDs)
        allowed = {'name', 'default_code', 'list_price', 'standard_price', 'type', 'description', 'description_sale'}
        for i, record in enumerate(data[:batch_size]):
            if not isinstance(record, dict):
                results['errors'].append({'line': i + 1, 'error': 'Record must be a dict'})
                continue
            try:
                if not record.get('name'):
                    results['errors'].append({'line': i + 1, 'error': 'Name is required'})
                    continue
                if validate_only:
                    results['processed'] += 1
                    continue
                vals = {k: v for k, v in record.items() if k in allowed}
                existing = False
                if record.get('default_code'):
                    existing = product_model.search([('default_code', '=', record['default_code'])], limit=1)
                if existing and update_existing:
                    existing.write(vals)
                    results['updated'] += 1
                elif existing:
                    results['skipped'] += 1
                else:
                    product_model.create(vals)
                    results['created'] += 1
                results['processed'] += 1
            except Exception as e:
                results['errors'].append({'line': i + 1, 'error': str(e)})
        return results

    def _import_leads(self, env, data, validate_only, batch_size, update_existing):
        """Import lead records (crm.lead)."""
        results = {
            'total_records': len(data),
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }
        lead_model = env['crm.lead'].sudo()
        allowed = {'name', 'partner_name', 'email_from', 'phone', 'description', 'type', 'user_id', 'team_id'}
        for i, record in enumerate(data[:batch_size]):
            if not isinstance(record, dict):
                results['errors'].append({'line': i + 1, 'error': 'Record must be a dict'})
                continue
            try:
                if not record.get('name'):
                    results['errors'].append({'line': i + 1, 'error': 'Name is required'})
                    continue
                if validate_only:
                    results['processed'] += 1
                    continue
                vals = {k: v for k, v in record.items() if k in lead_model._fields and k in allowed}
                if 'type' not in vals:
                    vals['type'] = 'opportunity'
                existing = False
                if record.get('email_from'):
                    existing = lead_model.search([('email_from', '=', record['email_from'])], limit=1)
                if existing and update_existing:
                    existing.write(vals)
                    results['updated'] += 1
                elif existing:
                    results['skipped'] += 1
                else:
                    lead_model.create(vals)
                    results['created'] += 1
                results['processed'] += 1
            except Exception as e:
                results['errors'].append({'line': i + 1, 'error': str(e)})
        return results
