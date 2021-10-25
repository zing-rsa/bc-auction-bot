import os
from datetime import datetime, timedelta


now = datetime.now()

future = datetime.strptime('2021-10-25T08:05:00', "%Y-%m-%dT%H:%M:%S")

if now > future - timedelta(minutes=5):
    print( datetime.strptime(now, "%Y-%m-%dT%H:%M:%S") )



