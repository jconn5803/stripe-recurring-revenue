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

### 4.6 User Managing Their Subscription (Billing Portal)

The Billing Portal endpoint is `/payments/billing-portal`.

- It uses `stripe.billing_portal.Session.create`.
- The session uses the Stripe customer ID stored in the database.
- If a user does not have a linked Stripe customer, they receive an error.

### 4.7 Cancelled Subscription

#### 4.7.a User Decides to Cancel Their Subscription

When a user cancels in the Billing Portal, Stripe sends `customer.subscription.deleted` once the expiration time has elapsed.
The webhook updates the local subscription row to `status = 'cancelled'`.

### 4.8 User Fails to Pay for Their Subscription

The webhook listens for `invoice.payment_failed`, but currently only logs the event.
This is where you would add logic to:

- Notify the user.
- Mark the subscription as `past_due` in your database.
- Prompt them to update payment details via the Billing Portal.

## 5. Testing

## 6. Deployment to Production
