"""
Unit tests for Stripe webhook handlers.
"""
import pytest
from unittest.mock import patch, MagicMock
from app import db
from app.models import User, Customer, Subscription
from app.payments.webhook_helpers import (
    handle_checkout_session,
    handle_subscription_cancelled,
    handle_invoice_payment_failed
)
from tests.fixtures.stripe_fixtures import (
    mock_checkout_session,
    mock_stripe_customer,
    mock_subscription
)


class TestHandleCheckoutSession:
    """Tests for handle_checkout_session webhook handler."""

    def test_creates_customer_record(self, app, sample_user):
        """Test that checkout session creates a Customer record."""
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            
            session = mock_checkout_session(
                customer_id='cus_new123',
                subscription_id='sub_new123',
                client_reference_id=str(user.id)
            )
            
            with patch('stripe.Customer.retrieve') as mock_cust_retrieve, \
                 patch('stripe.Subscription.retrieve') as mock_sub_retrieve:
                
                mock_cust_retrieve.return_value = mock_stripe_customer(
                    customer_id='cus_new123',
                    name='Test User'
                )
                mock_sub_retrieve.return_value = mock_subscription(
                    subscription_id='sub_new123',
                    customer_id='cus_new123'
                )
                
                handle_checkout_session(session)
                
                # Verify Customer was created
                customer = db.session.scalar(
                    db.select(Customer).where(Customer.stripe_customer_id == 'cus_new123')
                )
                assert customer is not None
                assert customer.user_id == user.id
                assert customer.stripe_customer_id == 'cus_new123'
                assert customer.customer_name == 'Test User'

    def test_creates_subscription_record(self, app, sample_user):
        """Test that checkout session creates a Subscription record."""
        with app.app_context():
            user = db.session.get(User, sample_user.id)
            
            session = mock_checkout_session(
                customer_id='cus_sub_test',
                subscription_id='sub_sub_test',
                client_reference_id=str(user.id)
            )
            
            with patch('stripe.Customer.retrieve') as mock_cust_retrieve, \
                 patch('stripe.Subscription.retrieve') as mock_sub_retrieve:
                
                mock_cust_retrieve.return_value = mock_stripe_customer(customer_id='cus_sub_test')
                mock_sub_retrieve.return_value = mock_subscription(
                    subscription_id='sub_sub_test',
                    customer_id='cus_sub_test',
                    status='active',
                    product_id='prod_premium',
                    price_id='price_monthly'
                )
                
                handle_checkout_session(session)
                
                # Verify Subscription was created
                subscription = db.session.scalar(
                    db.select(Subscription).where(Subscription.stripe_subscription_id == 'sub_sub_test')
                )
                assert subscription is not None
                assert subscription.status == 'active'
                assert subscription.product_id == 'prod_premium'
                assert subscription.price_id == 'price_monthly'

    def test_updates_existing_customer_name(self, app, sample_user, sample_customer):
        """Test that existing customer name is updated on checkout."""
        with app.app_context():
            customer = db.session.scalar(
                db.select(Customer).where(Customer.id == sample_customer.id)
            )
            original_customer_id = customer.stripe_customer_id
            
            session = mock_checkout_session(
                customer_id=original_customer_id,
                subscription_id='sub_update_test',
                client_reference_id=str(sample_user.id)
            )
            
            with patch('stripe.Customer.retrieve') as mock_cust_retrieve, \
                 patch('stripe.Subscription.retrieve') as mock_sub_retrieve:
                
                mock_cust_retrieve.return_value = mock_stripe_customer(
                    customer_id=original_customer_id,
                    name='Updated Name'
                )
                mock_sub_retrieve.return_value = mock_subscription(
                    subscription_id='sub_update_test',
                    customer_id=original_customer_id
                )
                
                handle_checkout_session(session)
                
                # Verify Customer name was updated
                updated_customer = db.session.scalar(
                    db.select(Customer).where(Customer.stripe_customer_id == original_customer_id)
                )
                assert updated_customer.customer_name == 'Updated Name'


class TestHandleSubscriptionCancelled:
    """Tests for handle_subscription_cancelled webhook handler."""

    def test_updates_subscription_status_to_cancelled(self, app, sample_subscription):
        """Test that subscription status is updated to cancelled."""
        with app.app_context():
            subscription = db.session.get(Subscription, sample_subscription.id)
            assert subscription.status == 'active'
            
            session = {'id': subscription.stripe_subscription_id}
            
            handle_subscription_cancelled(session)
            
            # Re-fetch and verify status
            updated_subscription = db.session.get(Subscription, subscription.id)
            assert updated_subscription.status == 'cancelled'

    def test_handles_nonexistent_subscription(self, app):
        """Test graceful handling of non-existent subscription."""
        with app.app_context():
            session = {'id': 'sub_nonexistent'}
            
            # Should not raise an exception
            handle_subscription_cancelled(session)


class TestHandleInvoicePaymentFailed:
    """Tests for handle_invoice_payment_failed webhook handler."""

    def test_updates_subscription_status_to_past_due(self, app, sample_subscription):
        """Test that subscription status is updated to past_due."""
        with app.app_context():
            subscription = db.session.get(Subscription, sample_subscription.id)
            assert subscription.status == 'active'
            
            session = {'id': subscription.stripe_subscription_id}
            
            handle_invoice_payment_failed(session)
            
            # Re-fetch and verify status
            updated_subscription = db.session.get(Subscription, subscription.id)
            assert updated_subscription.status == 'past_due'

    def test_handles_nonexistent_subscription(self, app):
        """Test graceful handling of non-existent subscription."""
        with app.app_context():
            session = {'id': 'sub_nonexistent'}
            
            # Should not raise an exception
            handle_invoice_payment_failed(session)
