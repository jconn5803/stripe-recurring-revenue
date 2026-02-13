from datetime import datetime
import stripe
from app import db
from app.models import Customer, Subscription


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
    


def handle_invoice_payment_failed(session):
    """
    Handle a failed invoice payment event from Stripe.
    
    This function processes an invoice payment failure by:
    1. Retrieving the associated subscription and customer from the database
    2. Updating the subscription status to 'past_due'
    
    Args:
        session (dict): The Stripe invoice object containing subscription and customer data
    
    Returns:
        None
        
    Note:
        Requires active database session and Stripe API access
    """
    subscription_id = session.get('id')
    subscription = db.session.scalar(db.select(Subscription).where(Subscription.stripe_subscription_id == subscription_id))
    
    if subscription:
        # Update subscription status to 'past_due'
        subscription.status = 'past_due'
        db.session.commit()

def handle_subscription_updated(session):
    """
    Handle a subscription update event from Stripe.
    
    This function processes a subscription update by:
    1. Retrieving the associated subscription from the database
    2. Updating the subscription status and other relevant fields based on the new data
    
    Args:
        session (dict): The Stripe subscription object containing updated subscription data
    
    Returns:
        None
        
    Note:
        Requires active database session and Stripe API access
    """
    subscription_id = session.get('id')
    subscription = db.session.scalar(db.select(Subscription).where(Subscription.stripe_subscription_id == subscription_id))
    
    if subscription:
        # Update subscription status and other relevant fields
        subscription.status = session.get('status')
        # You can also update other fields like product_id, price_id, etc. if needed
        db.session.commit()