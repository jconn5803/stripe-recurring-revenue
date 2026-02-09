import os
import stripe
from flask import render_template, current_app
from flask_login import login_required, current_user
from app.general import bp


@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')


@bp.route('/access')
@login_required
def access():
    stripe.api_key = os.getenv('TEST_STRIPE_SECRET_KEY')
    if not stripe.api_key:
        current_app.logger.error("Stripe API key missing: TEST_STRIPE_SECRET_KEY is not set")
        return render_template(
            'access.html',
            title='Access',
            error="Stripe API key is not configured."
        )

    customer = current_user.customer
    if not customer:
        return render_template(
            'access.html',
            title='Access',
            error="No Stripe customer is linked to your account."
        )

    try:
        entitlements = stripe.entitlements.ActiveEntitlement.list(
            customer=customer.stripe_customer_id,
            limit=100
        )
    except stripe.error.StripeError as exc:
        current_app.logger.error(f"Stripe error checking entitlements: {exc}")
        return render_template(
            'access.html',
            title='Access',
            error="There was a problem checking your subscription status."
        )

    entitlement_keys = sorted({e.lookup_key for e in entitlements.data if e.lookup_key})
    has_test_access = "test-access" in entitlement_keys
    has_test_access_2 = "test-access-2" in entitlement_keys

    return render_template(
        'access.html',
        title='Access',
        entitlement_keys=entitlement_keys,
        has_test_access=has_test_access,
        has_test_access_2=has_test_access_2
    )
