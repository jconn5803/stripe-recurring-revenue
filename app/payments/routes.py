from flask import request, jsonify, redirect
import stripe
import os
from app.payments import bp


import os

# Nuke any proxy config that might be injected
for k in ["HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(k, None)



@bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    
    # Use the test secret key configured in .env
    stripe.api_key = os.getenv('TEST_STRIPE_SECRET_KEY')
    # Choose the appropriate Stripe Price ID based on the selected plan
    price_id = os.getenv('TEST_MONTHLY_PRICE_ID')

    if not price_id:
        return jsonify({'error': 'Price configuration is missing.'}), 400

    base_url = request.host_url.rstrip('/')
    print(base_url)

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
