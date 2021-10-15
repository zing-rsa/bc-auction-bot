import os
import requests
from discord.ext import commands

url = 'https://opencnft.io/api/project/GP2aXZGkrjt8PJYyPwO/tx'

TOKEN = os.getenv('TOKEN')

for i in range(3):
    x = requests.post(url, data = { 'Page': i })
    print(x.text)
