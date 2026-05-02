## AI Options Advisor README


## What the application does
Options Advisor is a Flask web application that lets users visualize and analyze options strategies on any US-listed equity. Users can pull live options chains, build single- or multi-leg strategies, and see interactive P/L diagrams with Greeks (delta, gamma, theta, vega) computed via a Black-Scholes pricing engine. An AI advisor powered by Claude accepts plain-English market views ("I think TSLA stays flat for 30 days") and recommends concrete strategies with full risk/reward analysis.

## How to run the application
Step 1: Go to following [Final Project URL](https://final-options-advisor.onrender.com)

Step 2: Enter a valid Anthopic API Key (Follow instructions on page if you don't have one)

Step 3: Click enter and enjoy my AI options strategy builder application!!


## Any required API keys or setup steps
- Anthropic API Key is needed for the application. When you visit the app, you will be prompted to enter your key on the login screen; it is validated against the Anthropic API and stored in an encrypted session for 24 hours, never persisted on the server. 
- Options chain data is sourced via yfinance with approximately 15-minute delay and requires no API key or signup.