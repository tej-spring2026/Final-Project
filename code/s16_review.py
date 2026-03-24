# Chapter 11: Tuples - Immutable Sequences
# A tuple is an immutable sequence of values. Once a tuple is created, it cannot be modified. Tuples are defined using parentheses () and can contain any number of elements, including zero. They are often used to group related data together.

# Once the data from yfinance is loaded, we can access the information about the company using the info dictionary. We can also modify the values in the dictionary and add new key-value pairs as needed.
import yfinance as yf

stock = yf.Ticker('AAPL')
info = stock.info
print(info['shortName'])     # 'Apple Inc.'
print(info['currentPrice'])  # 229.87


# print(info['longBusinessSummary'])
from distro import info


print(info['longBusinessSummary'].split())
print('iphone' in info['longBusinessSummary'].split())

print('iPhone' in info['longBusinessSummary'])

print(info['city'])
# info['city'][0] = 'c'
info['city'] = 'Wellesley'
print(info['city'])

info['founder'] = 'Robert'
print(info['founder'])

# If data starts in [], then the data type is a list of dictionaries
# We do it as this to attrubute mutliple pieces of information to the same key, for example, the different executives of a company



for k, v in info.items():
    print(k, v)

tickers = ['AAPL', 'NVDA', 'MSFT']
prices = {}
for t in tickers:
    prices[t] = yf.Ticker(t).info['currentPrice']

print(prices)
print(sorted(prices)) #Creates a new list of the keys in prices, sorted alphabetically
print(sorted(prices.keys())) # Same as above
print(sorted(prices.values(), reverse=True)) # Creates a new list of the values in prices, sorted from highest to lowest

# print(tickers)

# Ultimate lesson, we need to know the structure of our data

tickers.append('GOOG') # How to add to a list
print(tickers)




