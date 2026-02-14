import os
base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(base_dir, 'app.db')
    
    # Stripe configuration
    STRIPE_SECRET_KEY = os.environ.get('TEST_STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('TEST_STRIPE_WEBHOOK_SECRET')
    STRIPE_MONTHLY_PRICE_ID = os.environ.get('TEST_MONTHLY_PRICE_ID')
    STRIPE_YEARLY_PRICE_ID = os.environ.get('TEST_YEARLY_PRICE_ID')


class TestConfig(Config):
    """Configuration for testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    
    # Mock Stripe keys for testing
    STRIPE_SECRET_KEY = 'sk_test_mock_key'
    STRIPE_WEBHOOK_SECRET = 'whsec_test_mock_secret'
    STRIPE_MONTHLY_PRICE_ID = 'price_test_monthly'
    STRIPE_YEARLY_PRICE_ID = 'price_test_yearly'