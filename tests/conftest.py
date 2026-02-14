"""
Pytest configuration and fixtures for Flask app testing.
"""
import pytest
from unittest.mock import MagicMock, patch
from app import create_app, db
from app.models import User, Customer, Subscription
from config import TestConfig


@pytest.fixture(scope='function')
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Provides a database session for testing."""
    with app.app_context():
        yield db.session


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        user = User(
            email='test@example.com',
            name='Test User'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Re-fetch to ensure attached to session
        user = db.session.get(User, user.id)
        yield user


@pytest.fixture
def sample_customer(app, sample_user):
    """Create a sample customer linked to a user."""
    with app.app_context():
        user = db.session.get(User, sample_user.id)
        customer = Customer(
            user_id=user.id,
            stripe_customer_id='cus_test123456',
            customer_name='Test User'
        )
        db.session.add(customer)
        db.session.commit()
        
        customer = db.session.get(Customer, customer.id)
        yield customer


@pytest.fixture
def sample_subscription(app, sample_customer):
    """Create a sample subscription for testing."""
    with app.app_context():
        customer = db.session.scalar(
            db.select(Customer).where(Customer.id == sample_customer.id)
        )
        subscription = Subscription(
            stripe_customer_id=customer.stripe_customer_id,
            stripe_subscription_id='sub_test123456',
            status='active',
            product_id='prod_test123',
            price_id='price_test123'
        )
        db.session.add(subscription)
        db.session.commit()
        
        subscription = db.session.get(Subscription, subscription.id)
        yield subscription


@pytest.fixture
def authenticated_client(app, client, sample_user):
    """A test client with an authenticated user session."""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['_user_id'] = str(sample_user.id)
            sess['_fresh'] = True
    return client


@pytest.fixture
def mock_stripe():
    """Mock the stripe module for testing."""
    with patch('stripe.checkout.Session.create') as mock_checkout, \
         patch('stripe.Customer.retrieve') as mock_customer, \
         patch('stripe.Subscription.retrieve') as mock_subscription, \
         patch('stripe.billing_portal.Session.create') as mock_portal, \
         patch('stripe.Webhook.construct_event') as mock_webhook, \
         patch('stripe.entitlements.ActiveEntitlement.list') as mock_entitlements:
        
        yield {
            'checkout_create': mock_checkout,
            'customer_retrieve': mock_customer,
            'subscription_retrieve': mock_subscription,
            'portal_create': mock_portal,
            'webhook_construct': mock_webhook,
            'entitlements_list': mock_entitlements
        }
