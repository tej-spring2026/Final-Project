from flask import Flask, render_template
from stocks import get_stock_price

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('hello.html')


@app.route('/stock/<ticker>')
def stock_price(ticker):
    price = get_stock_price(ticker)
    if price is None:
        return f"Could not find price for ticker: {ticker.upper()}", 404
    return price


@app.route('/hello/<name>')
def hello_name(name):
    return f'Hello, {name}!'


@app.route('/square/<int:n>')
def square(n):
    return f'{n} squared is {n ** 2}'


if __name__ == '__main__':
    app.run(debug=True)
