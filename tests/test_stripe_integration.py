"""
Integration tests using real Stripe test mode API.

These tests require valid Stripe test mode API keys to be set in the environment.
They are marked with @pytest.mark.integration and can be skipped when running
unit tests only.

To run integration tests:
    pytest tests/test_stripe_integration.py -v -m integration

To skip integration tests:
    pytest tests/ -v -m "not integration"
"""
import pytest
import os
import stripe

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def stripe_configured():
    """Check if Stripe test keys are configured."""
    return bool(os.getenv('TEST_STRIPE_SECRET_KEY'))


@pytest.fixture(scope='module')
def stripe_client():
    """Configure Stripe with test API key."""
    api_key = os.getenv('TEST_STRIPE_SECRET_KEY')
    if not api_key:
        pytest.skip('TEST_STRIPE_SECRET_KEY not set')
    
    stripe.api_key = api_key
    return stripe


class TestStripeCheckoutIntegration:
    """Integration tests for Stripe Checkout."""

    @pytest.mark.skipif(not stripe_configured(), reason='Stripe keys not configured')
    def test_create_checkout_session_returns_valid_url(self, stripe_client):
        """Test that a real checkout session can be created."""
        price_id = os.getenv('TEST_MONTHLY_PRICE_ID')
        if not price_id:
            pytest.skip('TEST_MONTHLY_PRICE_ID not set')
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url='http://localhost/success',
            cancel_url='http://localhost/cancel',
            client_reference_id='test_user_123'
        )
        
        assert session.id.startswith('cs_test_')
        assert session.url.startswith('https://checkout.stripe.com')
        assert session.status == 'open'


class TestStripeBillingPortalIntegration:
    """Integration tests for Stripe Billing Portal."""

    @pytest.mark.skipif(not stripe_configured(), reason='Stripe keys not configured')
    def test_create_portal_session_for_existing_customer(self, stripe_client):
        """Test creating a billing portal session for an existing customer."""
        # This test requires a real customer ID from your Stripe test account
        # You may want to create a test customer fixture or skip this test
        
        # First, create a test customer
        customer = stripe.Customer.create(
            email='integration_test@example.com',
            name='Integration Test User',
            metadata={'test': 'true'}
        )
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer.id,
                return_url='http://localhost/'
            )
            
            assert session.id.startswith('bps_')
            assert session.url.startswith('https://billing.stripe.com')
            assert session.customer == customer.id
        finally:
            # Clean up: delete the test customer
            stripe.Customer.delete(customer.id)


class TestStripeCustomerIntegration:
    """Integration tests for Stripe Customer API."""

    @pytest.mark.skipif(not stripe_configured(), reason='Stripe keys not configured')
    def test_create_and_retrieve_customer(self, stripe_client):
        """Test creating and retrieving a customer."""
        # Create customer
        customer = stripe.Customer.create(
            email='test_create@example.com',
            name='Test Create User',
            metadata={'test': 'true'}
        )
        
        try:
            assert customer.id.startswith('cus_')
            assert customer.email == 'test_create@example.com'
            
            # Retrieve customer
            retrieved = stripe.Customer.retrieve(customer.id)
            assert retrieved.id == customer.id
            assert retrieved.name == 'Test Create User'
        finally:
            # Clean up
            stripe.Customer.delete(customer.id)


class TestStripeEntitlementsIntegration:
    """Integration tests for Stripe Entitlements API."""

    @pytest.mark.skipif(not stripe_configured(), reason='Stripe keys not configured')
    def test_list_entitlements_for_customer(self, stripe_client):
        """Test listing entitlements for a customer."""
        # Create a test customer
        customer = stripe.Customer.create(
            email='entitlements_test@example.com',
            metadata={'test': 'true'}
        )
        
        try:
            # List entitlements (should return empty for new customer)
            entitlements = stripe.entitlements.ActiveEntitlement.list(
                customer=customer.id
            )
            
            # New customer should have no entitlements
            assert entitlements.data == []
        finally:
            stripe.Customer.delete(customer.id)
