The purpose of this repo is to set up a simple web app where users have two recurring subscription models where there is a 7 day free trial. I am also interested in learning how the Stripe testing and time clock works. 

The user experience should look as below.

1) User goes onto website and does not have a subscription.
2) User starts a subscription via Stripe which has a 7 day free trial period which can be cancelled at any point. 
3) 7 days elapses and the user's payment is either taken and the subscription continues or they have cancelled during the trial period and access is revoked. 
4) The user subscription period time elapses and the user either has cancelled or not in which case payment is taken again for the new cycle.
5) Step 4 repeats indefinetly.

I have set up a simple Flask application which is to be hosted on a website. The website consists of a simple registration and login system and once logged in you can sign up for a monthly subscription or a yearly subscription. 

To test webhooks during development you need to use either the Stripe CLI or ngrok since the Flask app runs privately inside my own computer at localhost so a webhook in the application would not be reachable by Stripe. 

Ngrok///
Ngrok is a utility that allocates a temporary public URL for your local web server. While ngrok is running, the local server can receive requests from anywhere in the world through Ngrok's public URL. 
Once pyngrok is installed you can open up a new terminal and run `ngrok http 5000`. To configure this endpoint go onto the Stripe Webhook configuration page (Webhook Configuration page) and enter the ngrok URL with the /event or /payment or the name of webhook in your app. 
