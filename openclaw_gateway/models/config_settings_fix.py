# -*- coding: utf-8 -*-
"""Configuration Settings Fix - Resolves missing invoice digitalization fields"""

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettingsFix(models.TransientModel):
    """
    Extends res.config.settings to add missing fields that cause JavaScript errors.
    
    This fixes the error: "extract_in_invoice_digitalization_mode" field is undefined
    which prevents accessing Settings page in Odoo.
    """
    _inherit = 'res.config.settings'

    # Add the missing invoice digitalization field
    extract_in_invoice_digitalization_mode = fields.Selection([
        ('no_send', 'Do not digitalize'),
        ('auto_send', 'Digitalize automatically'),
        ('manual_send', 'Digitalize manually'),
    ], string='Invoice Digitalization Mode', 
       default='no_send',
       help='Controls how invoices are processed for digital extraction')
    
    # Related fields that might also be missing
    invoice_digitalization_enabled = fields.Boolean(
        string='Enable Invoice Digitalization',
        default=False,
        help='Enable AI-powered invoice data extraction'
    )
    
    invoice_extraction_confidence_threshold = fields.Float(
        string='Extraction Confidence Threshold',
        default=0.8,
        help='Minimum confidence level for automatic extraction (0.0 to 1.0)'
    )

    @api.model
    def get_values(self):
        """Override to provide default values for missing config parameters."""
        res = super(ResConfigSettingsFix, self).get_values()
        
        # Get system parameters with safe defaults
        params = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'extract_in_invoice_digitalization_mode': params.get_param(
                'account.extract_in_invoice_digitalization_mode', 'no_send'
            ),
            'invoice_digitalization_enabled': params.get_param(
                'account.invoice_digitalization_enabled', False
            ),
            'invoice_extraction_confidence_threshold': float(params.get_param(
                'account.invoice_extraction_confidence_threshold', '0.8'
            )),
        })
        
        return res

    def set_values(self):
        """Override to save the configuration parameters."""
        super(ResConfigSettingsFix, self).set_values()
        
        params = self.env['ir.config_parameter'].sudo()
        
        # Save the digitalization settings
        params.set_param('account.extract_in_invoice_digitalization_mode', 
                        self.extract_in_invoice_digitalization_mode)
        params.set_param('account.invoice_digitalization_enabled', 
                        self.invoice_digitalization_enabled)
        params.set_param('account.invoice_extraction_confidence_threshold', 
                        self.invoice_extraction_confidence_threshold)

    @api.model
    def _fix_missing_fields_warning(self):
        """Log information about the fields we're adding to fix JS errors."""
        _logger.info("OpenClaw Gateway: Added missing invoice digitalization fields to prevent Settings page errors")
        return True