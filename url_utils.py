"""
URL Utilities for ET-FOOD Telegram Bot
Provides clean URL construction for webhooks and web interfaces across environments
"""

import os
import logging

logger = logging.getLogger(__name__)

def get_base_url():
    """
    Get clean base URL for the current environment
    
    Returns:
        str: Clean base URL without protocol (e.g., 'example.com' or 'localhost')
    """
    # Priority order: RENDER_EXTERNAL_URL > REPLIT_DEV_DOMAIN > localhost
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
    
    if render_url:
        base_url = render_url
    elif replit_domain:
        base_url = replit_domain
    else:
        base_url = 'localhost'
    
    # Strip any existing protocol
    base_url = base_url.replace('https://', '').replace('http://', '')
    
    return base_url

def construct_url(path='', https=True):
    """
    Construct a clean URL for the current environment
    
    Args:
        path (str): Path to append (with or without leading slash)
        https (bool): Whether to use HTTPS (default: True)
    
    Returns:
        str: Complete URL (e.g., 'https://example.com/path')
    """
    base_url = get_base_url()
    protocol = 'https' if https else 'http'
    
    # Ensure path starts with slash if provided
    if path and not path.startswith('/'):
        path = '/' + path
    
    url = f"{protocol}://{base_url}{path}"
    
    logger.debug(f"Constructed URL: {url}")
    return url

def construct_webhook_url(endpoint):
    """
    Construct webhook URL for Telegram bots
    
    Args:
        endpoint (str): Webhook endpoint (e.g., 'webhook' or 'driver-webhook')
    
    Returns:
        str: Complete webhook URL
    """
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    
    url = construct_url(endpoint)
    logger.info(f"Webhook URL constructed: {url}")
    return url

def construct_driver_panel_url(order_id, driver_id):
    """
    Construct driver panel URL with parameters
    
    Args:
        order_id (int): Order ID
        driver_id (int): Driver ID
    
    Returns:
        str: Complete driver panel URL
    """
    path = f"/driver-panel?order_id={order_id}&driver_id={driver_id}"
    url = construct_url(path)
    logger.debug(f"Driver panel URL constructed: {url}")
    return url