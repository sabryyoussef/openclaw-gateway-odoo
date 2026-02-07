# OpenClaw Gateway - Odoo Module

## Overview
OpenClaw Gateway is an Odoo 18 module that provides REST API endpoints for N8N workflow integration, enabling automated lead creation and CRM operations.

## Features
- ✅ REST API endpoints for lead creation
- ✅ Token-based authentication
- ✅ N8N workflow integration
- ✅ Multiple skills support (create_lead, customers, sales, etc.)
- ✅ Request logging and monitoring

## Installation
1. Upload module to Odoo instance
2. Update Apps list
3. Install "OpenClaw Gateway" module
4. Configure API tokens in Settings > OpenClaw > API Tokens

## API Endpoints
- **Base URL**: `/api/skills/`
- **Authentication**: `X-OPENCLAW-TOKEN` header
- **Primary Endpoint**: `/api/skills/create_lead`

## N8N Integration
This module powers N8N → Odoo lead creation workflows with simple HTTP requests.

## Version
- **Odoo**: 18.0
- **Module Version**: 1.0.0
- **Last Updated**: February 2026
