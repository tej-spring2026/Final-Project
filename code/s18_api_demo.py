pip install requests

import requests

response = requests.get('https://oim.108122.xyz/words/random')
print(response.json())   # a random word!

import requests

response = requests.get(
    'https://oim.108122.xyz/words/random',
    headers={'X-Token': 'tejtej'},  # your first name x2
)
print(response.json())


import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('ae964ec68213ea78f384b45736a2fd42')

url = 
