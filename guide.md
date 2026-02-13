# Stripe + Flask Recurring Revenue Guide

This guide explains how the Stripe integration works in this Flask app and gives a beginner-friendly overview of the Stripe concepts used. It also documents the current app flow and where Stripe connects into it.

## 1. Introduction

### 1.1 App Flow (No Payments Yet)

Before Stripe comes into play, the app already provides:

- A homepage with Register and Login.
- A basic authentication system that is **not production-ready** (no email verification, weak security posture, no rate limiting, etc.). It is for learning only.
- Once logged in, users see buttons for Monthly and Yearly subscriptions, plus access to an Access page and a Premium page.

At a high level, the flow looks like this:

1. User registers and logs in.
2. User chooses Monthly or Yearly subscription.
3. User can view Access to see which entitlements they have.
4. If the user has the `test-access` entitlement, they can view the Premium page.

## 2. Stripe

This app uses Stripe Subscriptions with Checkout Sessions and Stripe Entitlements.

### 2.1 Customer Object

Stripe Customers represent the person or business paying. In this app:

- A Stripe customer is created automatically by Checkout.
- The customer ID is stored in the local `customers` table.
- The Stripe customer is mapped back to a local user via `user_id`.

### 2.2 Product Object

A Product is the thing you're selling. In this app:

- There is one Stripe Product.
- That product has two Prices: monthly and yearly.

### 2.3 Price Object

A Price defines how much and how often a customer is charged. In this app:

- There is a monthly price (`TEST_MONTHLY_PRICE_ID`).
- There is a yearly price (`TEST_YEARLY_PRICE_ID`).
- The Checkout session chooses which price based on a form field.

### 2.4 Features / Entitlement

Stripe Entitlements allow you to attach feature access to a subscription. In this app:

- Entitlements are checked using `stripe.entitlements.ActiveEntitlement.list`.
- The lookup keys used are `test-access` and `test-access-2`.
- `test-access` gates access to the Premium page.

## 3. Stripe and Flask (How They Communicate)

### 3.1 API

The app uses Stripe's Python SDK (`stripe==14.3.0`).

- Stripe API key is loaded from `TEST_STRIPE_SECRET_KEY`.
- The app does not explicitly set `stripe.api_version` in code, so it uses your account's configured API version (`2026-01-28.clover`).

### 3.2 Authentication

Authentication with Stripe is handled via secret keys set in environment variables:

- `TEST_STRIPE_SECRET_KEY` (used in routes and webhook)
- `TEST_STRIPE_WEBHOOK_SECRET` (used to verify incoming webhook signatures)

### 3.3 Events

Stripe Events are JSON payloads sent to your webhook. This app listens for:

- `checkout.session.completed`
- `invoice.paid`
- `invoice.payment_failed`
- `customer.subscription.deleted`

Only `checkout.session.completed` and `customer.subscription.deleted` are currently used to update the database.

### 3.4 Webhooks

Stripe sends subscription lifecycle updates to `/payments/event`.

- The webhook verifies the signature using `TEST_STRIPE_WEBHOOK_SECRET`.
- If the secret is missing, it accepts the event without signature verification (development-only behavior).

### 3.4.a Setting up Webhook in Development

Because Stripe can't reach `localhost`, you need a public URL:

1. Start your Flask app locally.
2. Run `ngrok http 5000`.
3. Take the public `https://...ngrok.io` URL and set a Stripe webhook endpoint in the dashboard.

Endpoint URL should be `https://...ngrok.io/payments/event`.

## 4. Stripe in My Test Flask Application

### 4.1 Solution Overview

The integration uses:

- Stripe Checkout Sessions for subscribing.
- Stripe Webhooks for creating customers/subscriptions in the local DB.
- Stripe Entitlements for feature gating.
- Stripe Billing Portal for subscription management.

### 4.2 Stripe Authentication

Stripe keys and IDs are read from environment variables:

- `TEST_STRIPE_SECRET_KEY`
- `TEST_STRIPE_WEBHOOK_SECRET`
- `TEST_MONTHLY_PRICE_ID`
- `TEST_YEARLY_PRICE_ID`

`stripe.api_key` is set in:

- `app/payments/routes.py`
- `app/payments/webhook.py`
- `app/general/routes.py`

Note: `app/payments/routes.py` removes proxy-related environment variables (`HTTPS_PROXY`, `ALL_PROXY`) to avoid Stripe request issues.

### 4.3 The Database (Tables and Data)

The database models are in `app/models.py`:

- `users`: stores email, name, password hash, and signup time.
- `customers`: stores Stripe customer ID and maps it to a local `user_id`.
- `subscriptions`: stores Stripe subscription ID, status, product ID, price ID, and creation time.

### 4.4 Creating a New Subscription

1. User clicks a Monthly or Yearly button on `index.html`.
2. The form posts to `/payments/create-checkout-session`.
3. The server picks a price ID from the environment (Monthly uses `TEST_MONTHLY_PRICE_ID`, Yearly uses `TEST_YEARLY_PRICE_ID`).
4. A Checkout Session is created in subscription mode.
5. `client_reference_id` is set to the logged-in user ID (so it can be mapped on webhook).
6. User is redirected to Stripe Checkout.
7. Once the user pays via a valid payment method this will trigger a new customer object to be created in Stipe and most importantly the checkout.session.completed event to be triggered. 
8. This event should trigger the webhook which in turn triggers the function `handle_checkout_session`. This retrives the Stripe customer ID and adds them to our customers database. Storing the Stripe customer ID against our internal user ID is essential for managing subsctiptions. Additionally, it will add a subscription record to our database (storing the Stripe subscription ID, status, product ID, price ID and creation time). Note: we just store this for record and we do not actually use this to manage access to features.
9. A Stripe event entitlements.active_entitlement_summary.updated is called which adds any features associated with the product the customer has bought to this list. This is what is used to manage access. 

### 4.5 Managing User Access to Features

Access control is handled in two places:

- `app/general/routes.py` -> `/access` lists active entitlements for the logged-in user.
- `app/payments/decorators.py` -> `@requires_feature('test-access')` gates `/premium`.

More detail on how the entitlement list is fetched and used:

1. The user must be logged in (`@login_required` on `/access`), otherwise they are redirected to login.
2. The route loads `TEST_STRIPE_SECRET_KEY` and fails fast if it is missing, returning a friendly error on the page.
3. The route pulls the local `Customer` record via `current_user.customer`. If there is no linked Stripe customer, it shows an error and does not call Stripe.
4. If a Stripe customer exists, it calls `stripe.entitlements.ActiveEntitlement.list(customer=customer.stripe_customer_id, limit=100)` to retrieve the active entitlements.
5. The response objects are reduced to a list of `lookup_key` values and then compared against known keys like `test-access` and `test-access-2`.
6. The UI renders the entitlement list and boolean flags (`has_test_access`, `has_test_access_2`) so users can see what features they currently have.

The decorator in `app/payments/decorators.py` applies the same logic at request time for `/premium`:

1. It loads the Stripe customer from the local database for the logged-in user.
2. It calls the same Stripe Entitlements API.
3. It checks whether any entitlement has a `lookup_key` that matches the required feature.
4. If the entitlement is missing, it flashes a message and redirects the user away from the premium page.

You could imagine using the first user access method when you want to manage feature access on the same endpoint, whereas decorators are more useful for managing full page access.

### 4.6 User Managing Their Subscription (Billing Portal)

The Billing Portal endpoint is `/payments/billing-portal`.

- It uses `stripe.billing_portal.Session.create`.
- The session uses the Stripe customer ID stored in the database.
- If a user does not have a linked Stripe customer, they receive an error.

On the billing portal the user can update their payment method, add new payment methods, see their invoice history and update billing info. Most importantly this is where the "cancel subscription" button lies. 


### 4.7 Cancelled Subscription

#### 4.7.a User Decides to Cancel Their Subscription

When a user cancels in the Billing Portal, Stripe sends `customer.subscription.deleted` once the expiration time has elapsed.
The webhook updates the local subscription row to `status = 'cancelled'`. Recall the subscriptions table is just for our record and does not actually control access.
When the expiration time has passed a entitlements.active_entitlement_summary.updated which removes the features from the entitlements list that the customer has lost. This means that these entitlements are no longer active. 

### 4.7.b User Fails to Pay for Their Subscription

The webhook listens for `invoice.payment_failed`, but currently only logs the event.

Within the Stripe dashboard you can configure smart retries. The default setting is to try up to 8 times in 2 weeks of the first payment failure and then cancel the subscription if all the retries fail. 
In the Stripe dashboard setting you can set up emails to customers with failed invoices with payment links to update their payment method. 

## 5. Free Trial
A free trial period is set up by adding to the stripe.checkout.session.create the argument subscription_data={"trial_period_days": 7}. This will then create a subscription as usual with the status of `trialing`. The user inputs their payment details so if they don't cancel then the payment is taken and the entitlements do not change.

### Cancelling during a Trial Period
A user has every right to cancel during a trial period. The user can cancel the free trial, and hence the subscription, via the billing portal. When the billing cycle ends, i.e the free trial elapses, the customer.subscription.deleted event is invoked which causes the same process as 4.7.a. 

## 6. Discount Codes
You may want to offer discount codes to customers for 10% or £30 off. You can do this by

1. Create a coupon via the Stripe dashboard product catalogue. Coupons are configurable for type, amounts, specific products, durations and usage quotas. Interestingly, it appears that if you have multiple prices associated with the same product then you can only apply it to the product as a whole. You are most likely going to want to toggle customer-facing coupon codes active. They are also configurable for a specific customer.
2. In the stripe.checkout.session.create add `allow_promotion_codes=True` as an argument.






## 7. Testing

## 8. Deployment to Production
