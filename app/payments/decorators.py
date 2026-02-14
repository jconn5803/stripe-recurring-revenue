from functools import wraps
from flask import current_app, redirect, url_for, flash
from flask_login import current_user
from app.models import Customer
import stripe

def requires_feature(feature_lookup_key):
    """
    Flask decorator that checks if the current user has access to a feature.
    Usage: @requires_feature('premium_reports')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get current user from Flask session/login system
            user = current_user
            
            # Check authentication first - current_user is AnonymousUserMixin when not logged in
            if not user.is_authenticated:
                flash('Please log in to access this feature.')
                return redirect(url_for('auth.login'))
            
            # Get the Stripe customer ID for this user
            stripe_customer = Customer.query.filter_by(user_id=user.id).first()
            
            if not stripe_customer:
                flash('You need a subscription to access this feature.')
                return redirect(url_for('auth.login'))
            
            try:
                # Check if user has this entitlement
                entitlements = stripe.entitlements.ActiveEntitlement.list(
                    customer=stripe_customer.stripe_customer_id
                )
                
                # Check if the requested feature is in the active entitlements
                has_feature = any(
                    e.lookup_key == feature_lookup_key
                    for e in entitlements.data
                )
                
                if not has_feature:
                    flash(f'Your subscription doesn\'t include access to this feature.')
                    return redirect(url_for('upgrade'))
                    
                return f(*args, **kwargs)
                
            except stripe.error.StripeError as e:
                current_app.logger.error(f"Stripe error checking entitlements: {e}")
                flash('There was a problem checking your subscription status.')
                return redirect(url_for('account'))
                
        return decorated_function
    return decorator