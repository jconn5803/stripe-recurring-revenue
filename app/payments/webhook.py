from flask import request, jsonify
import stripe
import os
import json
from app.payments import bp
from app.payments.webhook_helpers import handle_checkout_session, handle_invoice_payment_failed, handle_subscription_cancelled
from app import db

stripe.api_key = os.getenv('TEST_STRIPE_SECRET_KEY')


# This is the webhook endpoint that Stripe will call to inform you of events related to customers subscriptions and payments.
# Use Entitlements to provision the subscription.
# Continue to provision the subscription each billing cycle as you receive invoice.paid webhooks.
# If you receive a invoice.payment_failed event, you can notify the customer and send them to the
# customer portal to update their payment method. 
@bp.route('/event', methods=['POST'])
def event_received():
    webhook_secret = os.getenv('TEST_STRIPE_WEBHOOK_SECRET')
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret)
            data = event['data']
        except Exception as e:
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event['type']
    else:
        event_type = request_data['type']


    # As a minumum the events to monitor are checkout.session.completed, invoice.paid, and invoice.payment_failed.
    # checkout.session.completed is sent when a customer successfully completes the Checkout session, informing of a new purchase.
    # invoice.paid is sent each billing period when a invoice payment succeeds.
    # invoice.payment_failed is sent each billing period if theres an issue with your customer's payment method.

    if event_type == 'checkout.session.completed':
        # Payment is successful and the subscription is created.
        # You should provision the subscription and save the customer ID to your database.
        session = event['data']['object']
        handle_checkout_session(session)
    elif event_type == 'invoice.paid':
        session = event['data']['object']
        # Continue to provision the subscription as payments continue to be made.
        # Store the status in your database and check when a user accesses your service.
        # This approach helps you avoid hitting rate limits.
    elif event_type == 'invoice.payment_failed':
        # The payment failed or the customer doesn't have a valid payment method.
        # The subscription becomes past_due. Notify your customer and send them to the
        # customer portal to update their payment information.
        session = event['data']['object']
        handle_invoice_payment_failed(session)
    elif event_type == 'customer.subscription.deleted': # Case where user cancels subscrition via portal
        # Need to mark the subscription as cancelled in database
        session = event['data']['object']
        handle_subscription_cancelled(session)

    else:
        print('Unhandled event type {}'.format(event_type))

    return jsonify({'status': 'success'})
