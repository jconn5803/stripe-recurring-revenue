from flask import request, jsonify, redirect
from datetime import datetime
import stripe
import os
import json
from app.payments import bp
from app.models import User, Customer, Subscription
from app import db

stripe.api_key = os.getenv('TEST_STRIPE_SECRET_KEY')


@bp.route('/test', methods=['GET'])
def test_route():
    return """
    <html>
        <head><title>Test</title></head>
        <body>
            <h1>Hello world</h1>
        </body>
    </html>
    """


def handle_checkout_session(session):
    """
    Handle a Stripe checkout session completion event.
    This function processes a completed checkout session by:
    1. Creating or updating a Customer record in the database based on Stripe customer data
    2. Creating a Subscription record if a subscription was included in the checkout
    Args:
        session (dict): The Stripe checkout session object containing customer and subscription data
    Returns:
        None
    Side Effects:
        - Creates or updates Customer record in database
        - Creates Subscription record in database if subscription exists
        - Commits changes to database session
    Note:
        Requires active database session and Stripe API access
    """
    
    # 1. Deal with customer creation from the event
    stripe_customer_id = session.get('customer')
    user_id = session.get('client_reference_id')

    # Retrieve the customer data from Stripe
    stripe_customer = stripe.Customer.retrieve(stripe_customer_id)
    customer_name = stripe_customer.get('name')
    created_at = stripe_customer.get('created')

    # Create or update the Customer record in your database
    customer = db.session.scalar(db.select(Customer).where(Customer.stripe_customer_id == stripe_customer_id))
    if not customer:
        customer = Customer(
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            created_at=datetime.fromtimestamp(created_at),
            customer_name=customer_name
        )
        db.session.add(customer)
        db.session.commit()
    else:
        customer.customer_name = customer_name
        db.session.commit()
    
    # 2. Deal with subscription creation from the event
    subscription_id = session.get('subscription')
    if subscription_id:
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        product_id = stripe_subscription['items']['data'][0]['price']['product']
        price_id = stripe_subscription['items']['data'][0]['price']['id']
        subscription = Subscription(
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=subscription_id,
            status=stripe_subscription['status'],
            product_id=product_id,
            price_id=price_id,
            created_at=datetime.fromtimestamp(stripe_subscription['created'])
        )
        db.session.add(subscription)
        db.session.commit()

    
def handle_subscription_cancelled(session):
    """
    Handle the cancellation of a subscription.
    
    Updates the subscription status to 'cancelled' in the database when a 
    subscription cancellation event is received from Stripe webhook.
    
    Args:
        session (dict): The session data containing subscription information,
                       expected to have an 'id' key with the Stripe subscription ID.
    
    Returns:
        None
        
    Side Effects:
        - Updates the subscription status in the database to 'cancelled'
        - Commits the changes to the database session
    """
    subscription_id = session.get('id')
    subscription = db.session.scalar(db.select(Subscription).where(Subscription.stripe_subscription_id == subscription_id))
    if subscription:
        subscription.status = 'cancelled'
        db.session.commit()
    







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
        data = request_data['data']
        event_type = request_data['type']
    
    data_object = data['object']

    # As a minumum the events to monitor are checkout.session.completed, invoice.paid, and invoice.payment_failed.
    # checkout.session.completed is sent when a customer successfully completes the Checkout session, informing of a new purchase.
    # invoice.paid is sent each billing period when a invoice payment succeeds.
    # invoice.payment_failed is sent each billing period if theres an issue with your customer's payment method.

    if event_type == 'checkout.session.completed':
        # Payment is successful and the subscription is created.
        # You should provision the subscription and save the customer ID to your database.
        print(data)
        session = event['data']['object']
        handle_checkout_session(session)
    elif event_type == 'invoice.paid':
        # Continue to provision the subscription as payments continue to be made.
        # Store the status in your database and check when a user accesses your service.
        # This approach helps you avoid hitting rate limits.
        print(data)
    elif event_type == 'invoice.payment_failed':
        # The payment failed or the customer doesn't have a valid payment method.
        # The subscription becomes past_due. Notify your customer and send them to the
        # customer portal to update their payment information.
        print(data)
    elif event_type == 'customer.subscription.deleted': # Case where user cancels subscrition via portal
        # Need to mark the subscription as cancelled in database
        session = event['data']['object']
        handle_subscription_cancelled(session)

    else:
        print('Unhandled event type {}'.format(event_type))

    return jsonify({'status': 'success'})
