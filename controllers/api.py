# -*- coding: utf-8 -*-
"""API Controller for OpenClaw Gateway"""
import json
import time
import logging
from datetime import datetime

from odoo import http
from odoo.http import request, Response

from ..executors.bulk_import import BulkImportExecutor

_logger = logging.getLogger(__name__)


class OpenClawAPIController(http.Controller):
    """
    HTTP API Controller for OpenClaw skills execution.
    
    Endpoints:
    - GET  /api/health - Health check (no auth)
    - GET  /api/skills - List available skills (with auth)
    - POST /api/skills/<code> - Execute skill (with auth)
    """
    
    # ==================== Helper Methods ====================
    
    def _validate_token(self, token_value, skill_code=None, remote_addr=None):
        """
        Validate API token and check permissions.
        
        Args:
            token_value (str): Token from request header
            skill_code (str): Skill code to validate permission for
            remote_addr (str): Client IP address
            
        Returns:
            dict: Validation result with token_record and roles if valid
        """
        if not token_value:
            return {
                'valid': False,
                'error': 'MISSING_TOKEN',
                'message': 'X-OPENCLAW-TOKEN header is required'
            }
        
        try:
            Token = request.env['openclaw.api.token'].sudo()
            result = Token.validate_token(token_value, skill_code, remote_addr)
            return result
        except Exception as e:
            _logger.exception(f"Error validating token: {str(e)}")
            return {
                'valid': False,
                'error': 'VALIDATION_ERROR',
                'message': f'Token validation failed: {str(e)}'
            }
    
    def _json_response(self, data, status=200):
        """
        Return standardized JSON HTTP response.
        
        Args:
            data (dict): Response data
            status (int): HTTP status code
            
        Returns:
            Response: Odoo HTTP Response object
        """
        return Response(
            json.dumps(data, default=str),
            status=status,
            mimetype='application/json',
            headers={'Content-Type': 'application/json'}
        )
    
    def _log_request(self, token_name, endpoint, method, skill_code, 
                     request_data, response_data, status, error, duration_ms, 
                     remote_addr, user_agent):
        """
        Log API request to database (safe - won't break API on error).
        
        Args:
            token_name (str): Token name used
            endpoint (str): API endpoint called
            method (str): HTTP method
            skill_code (str): Skill code executed
            request_data (dict): Request payload
            response_data (dict): Response data
            status (str): 'ok' or 'error'
            error (str): Error message if failed
            duration_ms (int): Request duration in milliseconds
            remote_addr (str): Client IP
            user_agent (str): User agent string
        """
        try:
            request.env['openclaw.request.log'].sudo().create({
                'token_name': token_name,
                'endpoint': endpoint,
                'method': method,
                'skill_code': skill_code,
                'request_json': json.dumps(request_data, default=str) if request_data else '{}',
                'response_json': json.dumps(response_data, default=str) if response_data else '{}',
                'status': status,
                'error': error,
                'duration_ms': duration_ms,
                'remote_addr': remote_addr,
                'user_agent': user_agent,
            })
        except Exception as e:
            _logger.error(f"Failed to log API request: {str(e)}")
    
    def _get_token_from_request(self):
        """Extract token from request headers."""
        return request.httprequest.headers.get('X-OPENCLAW-TOKEN')
    
    def _get_remote_addr(self):
        """Get client IP address from request."""
        return request.httprequest.remote_addr or 'unknown'
    
    def _get_user_agent(self):
        """Get user agent from request."""
        return request.httprequest.headers.get('User-Agent', 'unknown')
    
    # ==================== Route 1: Health Check ====================
    
    @http.route('/api/health', type='http', auth='none', methods=['GET'], csrf=False)
    def health_check(self, **kwargs):
        """
        Health check endpoint - no authentication required.
        
        Returns:
            JSON: {"status": "ok", "version": "...", "timestamp": "..."}
        """
        response_data = {
            'status': 'ok',
            'version': '18.0.1.0.0',
            'timestamp': datetime.now().isoformat(),
            'service': 'OpenClaw Gateway API'
        }
        return self._json_response(response_data, status=200)
    
    # ==================== Route 2: List Skills ====================
    
    @http.route('/api/skills', type='http', auth='public', methods=['GET'], csrf=False)
    def list_skills(self, **kwargs):
        """
        List available skills for authenticated token.
        
        Headers:
            X-OPENCLAW-TOKEN: API token
            
        Returns:
            JSON: Array of skill objects or error
        """
        start_time = time.time()
        token_value = self._get_token_from_request()
        remote_addr = self._get_remote_addr()
        user_agent = self._get_user_agent()
        
        # Validate token
        validation = self._validate_token(token_value, skill_code=None, remote_addr=remote_addr)
        
        if not validation['valid']:
            duration_ms = int((time.time() - start_time) * 1000)
            error_response = {
                'success': False,
                'error': validation['error'],
                'message': validation['message']
            }
            
            # Log failed request
            self._log_request(
                token_name='invalid',
                endpoint='/api/skills',
                method='GET',
                skill_code=None,
                request_data={},
                response_data=error_response,
                status='error',
                error=validation['error'],
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            return self._json_response(error_response, status=401)
        
        # Get token record and allowed skills
        token_record = validation['token_record']
        
        try:
            # If token has allowed_skills specified, filter by those
            if token_record.allowed_skills:
                skills = token_record.allowed_skills
            else:
                # No restriction - return all active skills
                skills = request.env['openclaw.skill'].sudo().search([('active', '=', True)])
            
            # Format skill data
            skills_data = []
            for skill in skills.sorted('sequence'):
                skills_data.append({
                    'code': skill.code,
                    'name': skill.name,
                    'description': skill.description or '',
                    'executor': skill.executor,
                    'max_limit': skill.max_limit,
                })
            
            duration_ms = int((time.time() - start_time) * 1000)
            response_data = {
                'success': True,
                'data': {
                    'skills': skills_data,
                    'count': len(skills_data)
                }
            }
            
            # Update token usage
            token_record.sudo().update_usage()
            
            # Log successful request
            self._log_request(
                token_name=token_record.name,
                endpoint='/api/skills',
                method='GET',
                skill_code=None,
                request_data={},
                response_data=response_data,
                status='ok',
                error=None,
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            return self._json_response(response_data, status=200)
            
        except Exception as e:
            _logger.exception(f"Error listing skills: {str(e)}")
            duration_ms = int((time.time() - start_time) * 1000)
            error_response = {
                'success': False,
                'error': 'SERVER_ERROR',
                'message': f'Failed to list skills: {str(e)}'
            }
            
            # Log error
            self._log_request(
                token_name=token_record.name,
                endpoint='/api/skills',
                method='GET',
                skill_code=None,
                request_data={},
                response_data=error_response,
                status='error',
                error='SERVER_ERROR',
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            return self._json_response(error_response, status=500)
    
    # ==================== Route 3: Execute Skill ====================
    
    @http.route('/api/skills/<string:code>', type='http', auth='public', methods=['POST'], csrf=False)
    def execute_skill(self, code, **kwargs):
        """
        Execute a skill by code.
        
        Headers:
            X-OPENCLAW-TOKEN: API token
            Content-Type: application/json
            
        Body:
            JSON payload for skill execution (varies by skill)
            
        Returns:
            JSON: Skill execution result or error
        """
        start_time = time.time()
        token_value = self._get_token_from_request()
        remote_addr = self._get_remote_addr()
        user_agent = self._get_user_agent()
        
        # Parse request payload
        try:
            payload = json.loads(request.httprequest.data.decode('utf-8') or '{}')
        except json.JSONDecodeError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_response = {
                'success': False,
                'error': 'INVALID_JSON',
                'message': f'Invalid JSON payload: {str(e)}'
            }
            
            self._log_request(
                token_name='invalid',
                endpoint=f'/api/skills/{code}',
                method='POST',
                skill_code=code,
                request_data={'_raw_error': str(e)},
                response_data=error_response,
                status='error',
                error='INVALID_JSON',
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            return self._json_response(error_response, status=400)
        
        # Validate token with skill permission check
        validation = self._validate_token(token_value, skill_code=code, remote_addr=remote_addr)
        
        if not validation['valid']:
            duration_ms = int((time.time() - start_time) * 1000)
            error_response = {
                'success': False,
                'error': validation['error'],
                'message': validation['message']
            }
            
            self._log_request(
                token_name='invalid',
                endpoint=f'/api/skills/{code}',
                method='POST',
                skill_code=code,
                request_data=payload,
                response_data=error_response,
                status='error',
                error=validation['error'],
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            return self._json_response(error_response, status=401)
        
        # Get token record and user roles
        token_record = validation['token_record']
        user_roles = validation.get('roles', [])
        
        try:
            # Execute skill
            Skill = request.env['openclaw.skill'].sudo()
            result = Skill.run_skill(code, payload, user_roles=user_roles)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Determine status
            status = 'ok' if result.get('success') else 'error'
            error = result.get('error') if not result.get('success') else None
            
            # Update token usage
            token_record.sudo().update_usage()
            
            # Log request
            self._log_request(
                token_name=token_record.name,
                endpoint=f'/api/skills/{code}',
                method='POST',
                skill_code=code,
                request_data=payload,
                response_data=result,
                status=status,
                error=error,
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            # Return appropriate HTTP status
            http_status = 200 if result.get('success') else 400
            return self._json_response(result, status=http_status)
            
        except Exception as e:
            _logger.exception(f"Error executing skill {code}: {str(e)}")
            duration_ms = int((time.time() - start_time) * 1000)
            error_response = {
                'success': False,
                'error': 'EXECUTION_ERROR',
                'message': f'Failed to execute skill: {str(e)}',
                'skill': code
            }
            
            self._log_request(
                token_name=token_record.name,
                endpoint=f'/api/skills/{code}',
                method='POST',
                skill_code=code,
                request_data=payload,
                response_data=error_response,
                status='error',
                error='EXECUTION_ERROR',
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            
            return self._json_response(error_response, status=500)

    # ==================== Route 4: Bulk Operations ====================

    @http.route('/api/bulk/<string:operation>', type='http', auth='public', methods=['POST'], csrf=False)
    def bulk_operation(self, operation, **kwargs):
        """Handle bulk operations (import). Requires X-OPENCLAW-TOKEN and skill permission bulk_import."""
        start_time = time.time()
        remote_addr = self._get_remote_addr()
        user_agent = self._get_user_agent()
        token_value = self._get_token_from_request()

        if not token_value:
            return self._json_response({
                'success': False,
                'error': 'TOKEN_REQUIRED',
                'message': 'X-OPENCLAW-TOKEN header is required'
            }, 401)

        if operation not in ('import', 'export', 'update'):
            return self._json_response({
                'success': False,
                'error': 'INVALID_OPERATION',
                'message': 'operation must be import, export, or update'
            }, 400)

        try:
            payload = json.loads(request.httprequest.get_data(as_text=True) or '{}')
        except json.JSONDecodeError as e:
            return self._json_response({
                'success': False,
                'error': 'INVALID_JSON',
                'message': str(e)
            }, 400)

        skill_code = f'bulk_{operation}'
        validation = self._validate_token(token_value, skill_code=skill_code, remote_addr=remote_addr)
        if not validation['valid']:
            duration_ms = int((time.time() - start_time) * 1000)
            err = validation.get('message', validation.get('error', 'Unauthorized'))
            self._log_request(
                token_name='Invalid',
                endpoint=f'/api/bulk/{operation}',
                method='POST',
                skill_code=skill_code,
                request_data=payload,
                response_data={'success': False, 'error': validation.get('error'), 'message': err},
                status='error',
                error=validation.get('error'),
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            return self._json_response({
                'success': False,
                'error': validation.get('error', 'UNAUTHORIZED'),
                'message': err
            }, 401)

        token_record = validation['token_record']
        try:
            if operation == 'import':
                result = BulkImportExecutor().execute(request.env, payload)
            else:
                result = {'success': False, 'error': 'NOT_IMPLEMENTED', 'message': f'Bulk {operation} not implemented'}

            duration_ms = int((time.time() - start_time) * 1000)
            token_record.sudo().update_usage()
            self._log_request(
                token_name=token_record.name,
                endpoint=f'/api/bulk/{operation}',
                method='POST',
                skill_code=skill_code,
                request_data=payload,
                response_data=result,
                status='ok' if result.get('success') else 'error',
                error=result.get('error'),
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            status_code = 200 if result.get('success') else 400
            return self._json_response(result, status=status_code)
        except Exception as e:
            _logger.exception("Bulk %s error: %s", operation, e)
            duration_ms = int((time.time() - start_time) * 1000)
            err_resp = {'success': False, 'error': 'BULK_ERROR', 'message': str(e)}
            self._log_request(
                token_name=token_record.name,
                endpoint=f'/api/bulk/{operation}',
                method='POST',
                skill_code=skill_code,
                request_data=payload,
                response_data=err_resp,
                status='error',
                error='BULK_ERROR',
                duration_ms=duration_ms,
                remote_addr=remote_addr,
                user_agent=user_agent
            )
            return self._json_response(err_resp, 500)

    # ==================== Route 5: Workflow Job Status ====================

    @http.route('/api/workflow/status/<string:job_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def workflow_status(self, job_id, **kwargs):
        """Get workflow job status by job_id. No auth required (job_id acts as secret)."""
        try:
            job = request.env['openclaw.workflow.job'].sudo().search([('job_id', '=', job_id)], limit=1)
            if not job:
                return self._json_response({'success': False, 'error': 'JOB_NOT_FOUND'}, 404)
            result = {
                'job_id': job.job_id,
                'status': job.status,
                'progress': job.progress_percent,
                'workflow_type': job.workflow_type,
                'created_at': job.create_date.isoformat() if job.create_date else None,
                'error': job.error_message,
            }
            if job.result_json:
                try:
                    result['result'] = json.loads(job.result_json)
                except (TypeError, ValueError):
                    result['result'] = job.result_json
            return self._json_response({'success': True, 'data': result})
        except Exception as e:
            _logger.exception("Workflow status error: %s", e)
            return self._json_response({
                'success': False,
                'error': 'STATUS_ERROR',
                'message': str(e)
            }, 500)
