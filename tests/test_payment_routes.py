"""
Unit tests for payment routes.
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from app import db
from app.models import User, Customer, Subscription
from tests.fixtures.stripe_fixtures import (
    mock_checkout_session,
    mock_billing_portal_session,
    mock_webhook_event,
    mock_stripe_customer,
    mock_subscription
)


class TestCreateCheckoutSession:
    """Tests for POST /payments/create-checkout-session."""

    def test_creates_monthly_checkout_session(self, app, authenticated_client):
        """Test creating a checkout session for monthly subscription."""
        with patch.dict(os.environ, {
            'TEST_MONTHLY_PRICE_ID': 'price_test_monthly',
            'TEST_YEARLY_PRICE_ID': 'price_test_yearly'
        }):
            with patch('app.payments.routes.stripe.checkout.Session.create') as mock_create:
                mock_session = MagicMock()
                mock_session.url = 'https://checkout.stripe.com/test'
                mock_create.return_value = mock_session
                
                response = authenticated_client.post(
                    '/payments/create-checkout-session',
                    data={'subscription_type': 'monthly'}
                )
                
                # Should redirect to Stripe checkout
                assert response.status_code == 303
                assert response.location == 'https://checkout.stripe.com/test'
                
                # Verify Stripe was called with monthly price
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs['line_items'][0]['price'] == 'price_test_monthly'

    def test_creates_yearly_checkout_session(self, app, authenticated_client):
        """Test creating a checkout session for yearly subscription."""
        with patch.dict(os.environ, {
            'TEST_MONTHLY_PRICE_ID': 'price_test_monthly',
            'TEST_YEARLY_PRICE_ID': 'price_test_yearly'
        }):
            with patch('app.payments.routes.stripe.checkout.Session.create') as mock_create:
                mock_session = MagicMock()
                mock_session.url = 'https://checkout.stripe.com/test-yearly'
                mock_create.return_value = mock_session
                
                response = authenticated_client.post(
                    '/payments/create-checkout-session',
                    data={'subscription_type': 'yearly'}
                )
                
                assert response.status_code == 303
                
                # Verify Stripe was called with yearly price
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs['line_items'][0]['price'] == 'price_test_yearly'

    def test_invalid_subscription_type_returns_error(self, app, authenticated_client):
        """Test that invalid subscription type returns 400."""
        response = authenticated_client.post(
            '/payments/create-checkout-session',
            data={'subscription_type': 'invalid'}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_stripe_error_returns_400(self, app, authenticated_client):
        """Test that Stripe errors are handled gracefully."""
        with patch.dict(os.environ, {
            'TEST_MONTHLY_PRICE_ID': 'price_test_monthly'
        }):
            with patch('app.payments.routes.stripe.checkout.Session.create') as mock_create:
                mock_create.side_effect = Exception('Stripe API error')
                
                response = authenticated_client.post(
                    '/payments/create-checkout-session',
                    data={'subscription_type': 'monthly'}
                )
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'Stripe API error' in data['error']


class TestWebhookEvent:
    """Tests for POST /payments/event webhook endpoint."""

    def test_handles_checkout_session_completed(self, app, client, sample_user):
        """Test handling checkout.session.completed webhook."""
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            
            session_obj = mock_checkout_session(
                customer_id='cus_webhook_test',
                subscription_id='sub_webhook_test',
                client_reference_id=str(user.id)
            )
            event = mock_webhook_event('checkout.session.completed', session_obj)
            
            with patch.dict(os.environ, {'TEST_STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
                with patch('app.payments.webhook.stripe.Webhook.construct_event') as mock_construct, \
                     patch('app.payments.webhook_helpers.stripe.Customer.retrieve') as mock_cust, \
                     patch('app.payments.webhook_helpers.stripe.Subscription.retrieve') as mock_sub:
                    
                    mock_construct.return_value = event
                    mock_cust.return_value = mock_stripe_customer(customer_id='cus_webhook_test')
                    mock_sub.return_value = mock_subscription(
                        subscription_id='sub_webhook_test',
                        customer_id='cus_webhook_test'
                    )
                    
                    response = client.post(
                        '/payments/event',
                        data=json.dumps(event),
                        content_type='application/json',
                        headers={'stripe-signature': 'test_sig'}
                    )
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['status'] == 'success'

    def test_handles_subscription_deleted(self, app, client, sample_subscription):
        """Test handling customer.subscription.deleted webhook."""
        with app.app_context():
            sub_id = sample_subscription.stripe_subscription_id
            
            sub_obj = {'id': sub_id}
            event = mock_webhook_event('customer.subscription.deleted', sub_obj)
            
            with patch.dict(os.environ, {'TEST_STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
                with patch('app.payments.webhook.stripe.Webhook.construct_event') as mock_construct:
                    mock_construct.return_value = event
                    
                    response = client.post(
                        '/payments/event',
                        data=json.dumps(event),
                        content_type='application/json',
                        headers={'stripe-signature': 'test_sig'}
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify subscription was cancelled
                    updated_sub = db.session.get(Subscription, sample_subscription.id)
                    assert updated_sub.status == 'cancelled'

    def test_handles_invoice_payment_failed(self, app, client, sample_subscription):
        """Test handling invoice.payment_failed webhook."""
        with app.app_context():
            # invoice.payment_failed expects subscription_id in the 'id' field
            invoice_obj = {'id': sample_subscription.stripe_subscription_id}
            event = mock_webhook_event('invoice.payment_failed', invoice_obj)
            
            with patch.dict(os.environ, {'TEST_STRIPE_WEBHOOK_SECRET': 'whsec_test'}):
                with patch('app.payments.webhook.stripe.Webhook.construct_event') as mock_construct:
                    mock_construct.return_value = event
                    
                    response = client.post(
                        '/payments/event',
                        data=json.dumps(event),
                        content_type='application/json',
                        headers={'stripe-signature': 'test_sig'}
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify subscription status was updated
                    updated_sub = db.session.get(Subscription, sample_subscription.id)
                    assert updated_sub.status == 'past_due'


class TestBillingPortal:
    """Tests for GET /payments/billing-portal."""

    def test_redirects_to_stripe_portal(self, app, sample_user, sample_customer):
        """Test that authenticated user with customer is redirected to portal."""
        with app.app_context():
            client = app.test_client()
            
            # Log in the user
            with client.session_transaction() as sess:
                sess['_user_id'] = str(sample_user.id)
                sess['_fresh'] = True
            
            with patch('app.payments.routes.stripe.api_key', 'sk_test_mock'):
                with patch('app.payments.routes.stripe.billing_portal.Session.create') as mock_portal:
                    mock_session = MagicMock()
                    mock_session.url = 'https://billing.stripe.com/test'
                    mock_portal.return_value = mock_session
                    
                    response = client.get('/payments/billing-portal')
                    
                    assert response.status_code == 303
                    assert response.location == 'https://billing.stripe.com/test'

    def test_returns_error_when_no_customer(self, app, sample_user):
        """Test error when user has no linked Stripe customer."""
        with app.app_context():
            client = app.test_client()
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(sample_user.id)
                sess['_fresh'] = True
            
            with patch('app.payments.routes.stripe.api_key', 'sk_test_mock'):
                response = client.get('/payments/billing-portal')
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'No Stripe customer' in data['error']


class TestSuccessAndCancelPages:
    """Tests for success and cancel pages."""

    def test_success_page_renders(self, client):
        """Test that success page renders correctly."""
        response = client.get('/payments/success')
        assert response.status_code == 200
        assert b'Thank you for your subscription' in response.data

    def test_cancel_page_renders(self, client):
        """Test that cancel page renders correctly."""
        response = client.get('/payments/cancel')
        assert response.status_code == 200
        assert b'Payment Cancelled' in response.data
