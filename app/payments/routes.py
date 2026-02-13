from flask import request, jsonify, redirect
from flask_login import current_user, login_required
import stripe
import os
import json
from app.payments import bp

# Nuke any proxy config that might be injected
# There was a bug where I was getting 403 errors from Stripe because of a proxy config in the environment
# I am still unsure of the true root cause
for k in ["HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(k, None)

stripe.api_key = os.getenv('TEST_STRIPE_SECRET_KEY')

@bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():

    # Firstly we need to determine the price ID to use based on the selected plan. For simplicity, we'll assume a single plan for now.
    subscription_type = request.form.get('subscription_type', 'monthly')
    if subscription_type == 'monthly':
        price_id = os.getenv('TEST_MONTHLY_PRICE_ID')
    elif subscription_type == 'yearly':
        price_id = os.getenv('TEST_YEARLY_PRICE_ID')
    else:
        return jsonify({'error': 'Invalid subscription type.'}), 400


    if not price_id:
        return jsonify({'error': 'Price configuration is missing.'}), 400

    base_url = request.host_url.rstrip('/')
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
            'price': price_id,
            'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{base_url}/payments/success',
            cancel_url=f'{base_url}/payments/cancel',
            client_reference_id=current_user.get_id(), 
            allow_promotion_codes=True
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@bp.route('/success')
def success():
    return '''
    <html>
        <head><title>Payment Successful</title></head>
        <body>
            <h1>Thank you for your subscription!</h1>
            <p>Your payment was successful and your subscription is now active.</p>
            <a href="/">Return to Home</a>
        </body>
    </html>
    '''

@bp.route('/cancel')
def cancel():
    return '''
    <html>
        <head><title>Payment Cancelled</title></head>
        <body>
            <h1>Payment Cancelled</h1>
            <p>Your payment was cancelled. No charges were made.</p>
            <a href="/">Return to Home</a>
        </body>
    </html>
    '''

@bp.route('/billing-portal')
@login_required
def billing_portal():
    if not stripe.api_key:
        return jsonify({'error': 'Stripe API key is not configured.'}), 500

    customer = current_user.customer
    if not customer:
        return jsonify({'error': 'No Stripe customer is linked to your account.'}), 400

    base_url = request.host_url.rstrip('/')
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer.stripe_customer_id,
            return_url=base_url
        )
        return redirect(session.url, code=303)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


