## My Final Project Proposal

**What I'm building:**
A Flask-based web application that lets users build, visualize, and analyze multi-leg options strategies on real equities, with an AI advisor (Claude) that recommends strategies based on a user's market view and explains the risks in plain English.

**Why I chose this:** 
I've recently gotten more intereted in trading options wihtin the public markets. I'm starting to learn more about them so I thought it would be cool to build an AI options analyzer to further my knowledge while also builiding a tool to help analyze potential future trades. 

**Core features:**
- Search any US-listed ticker and pull a live (15-min delayed) options chain via the Tradier sandbox API, with strikes, bid/ask, volume, open interest, and Greeks
- Build single- or multi-leg options strategies (long calls/puts, vertical spreads, straddles, iron condors) through a Flask-based UI
- Interactive P/L diagram showing payoff at expiration, plus key metrics like max profit, max loss, breakevens, and net debit/credit
- Black-Scholes pricing engine with the four main Greeks (delta, gamma, theta, vega) computed for each leg and the overall position
- AI advisor (Claude) that takes a plain-English market view ("I think AAPL stays between $170-180 for 30 days") and recommends a strategy, with tool that builds the recommendation position directly onto the P/L chart

**What I don't know yet:**
- If the Black-Scholes model is the best path for getting the Greeks correctly in Python, I'll need to validate outputs against published values before trusting the charts
- How I can have users operate the application by themselves without using my personal claude API tokens
- I don't know how well the free options API will display accurate figures
- How I can better cater the AI trade recommendation for the user's specific risk-profile and market beliefs