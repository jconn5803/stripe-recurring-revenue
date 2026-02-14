"""
Mock Stripe response objects for testing.

These fixtures return dictionaries that match the structure of actual Stripe API responses.
"""
import time
from typing import Optional
from unittest.mock import MagicMock


def mock_checkout_session(
    session_id: str = 'cs_test_123456',
    customer_id: str = 'cus_test123456',
    subscription_id: str = 'sub_test123456',
    client_reference_id: str = '1',
    mode: str = 'subscription',
    status: str = 'complete',
    url: str = 'https://checkout.stripe.com/c/pay/cs_test_123456'
) -> dict:
    """Create a mock Stripe checkout session object."""
    return {
        'id': session_id,
        'object': 'checkout.session',
        'customer': customer_id,
        'subscription': subscription_id,
        'client_reference_id': client_reference_id,
        'mode': mode,
        'status': status,
        'url': url,
        'success_url': 'http://localhost/payments/success',
        'cancel_url': 'http://localhost/payments/cancel',
        'payment_status': 'paid',
        'created': int(time.time()),
    }


def mock_stripe_customer(
    customer_id: str = 'cus_test123456',
    name: str = 'Test User',
    email: str = 'test@example.com'
) -> dict:
    """Create a mock Stripe customer object."""
    return {
        'id': customer_id,
        'object': 'customer',
        'name': name,
        'email': email,
        'created': int(time.time()),
        'livemode': False,
        'metadata': {},
    }


def mock_subscription(
    subscription_id: str = 'sub_test123456',
    customer_id: str = 'cus_test123456',
    status: str = 'active',
    product_id: str = 'prod_test123',
    price_id: str = 'price_test123'
) -> dict:
    """Create a mock Stripe subscription object."""
    return {
        'id': subscription_id,
        'object': 'subscription',
        'customer': customer_id,
        'status': status,
        'created': int(time.time()),
        'current_period_start': int(time.time()),
        'current_period_end': int(time.time()) + 30 * 24 * 60 * 60,
        'items': {
            'object': 'list',
            'data': [{
                'id': 'si_test123',
                'object': 'subscription_item',
                'price': {
                    'id': price_id,
                    'object': 'price',
                    'product': product_id,
                    'unit_amount': 999,
                    'currency': 'usd',
                    'recurring': {
                        'interval': 'month',
                        'interval_count': 1
                    }
                },
                'quantity': 1
            }]
        },
        'livemode': False,
    }


def mock_invoice(
    invoice_id: str = 'in_test123456',
    subscription_id: str = 'sub_test123456',
    customer_id: str = 'cus_test123456',
    status: str = 'paid'
) -> dict:
    """Create a mock Stripe invoice object."""
    return {
        'id': invoice_id,
        'object': 'invoice',
        'subscription': subscription_id,
        'customer': customer_id,
        'status': status,
        'amount_due': 999,
        'amount_paid': 999 if status == 'paid' else 0,
        'currency': 'usd',
        'created': int(time.time()),
        'livemode': False,
    }


def mock_webhook_event(
    event_type: str,
    data_object: dict,
    event_id: str = 'evt_test123456'
) -> dict:
    """Create a mock Stripe webhook event."""
    return {
        'id': event_id,
        'object': 'event',
        'type': event_type,
        'data': {
            'object': data_object
        },
        'created': int(time.time()),
        'livemode': False,
        'api_version': '2023-10-16',
    }


def mock_billing_portal_session(
    session_id: str = 'bps_test123456',
    customer_id: str = 'cus_test123456',
    url: str = 'https://billing.stripe.com/p/session/test123'
) -> dict:
    """Create a mock Stripe billing portal session."""
    return {
        'id': session_id,
        'object': 'billing_portal.session',
        'customer': customer_id,
        'url': url,
        'return_url': 'http://localhost/',
        'created': int(time.time()),
        'livemode': False,
    }


def mock_active_entitlement(
    entitlement_id: str = 'ent_test123',
    lookup_key: str = 'premium_access',
    feature_id: str = 'feat_test123'
) -> MagicMock:
    """Create a mock Stripe active entitlement object."""
    entitlement = MagicMock()
    entitlement.id = entitlement_id
    entitlement.lookup_key = lookup_key
    entitlement.feature = feature_id
    return entitlement


def mock_entitlements_list(lookup_keys: list[str] = None) -> MagicMock:
    """Create a mock Stripe entitlements list response."""
    if lookup_keys is None:
        lookup_keys = ['premium_access']
    
    response = MagicMock()
    response.data = [mock_active_entitlement(lookup_key=key) for key in lookup_keys]
    return response
