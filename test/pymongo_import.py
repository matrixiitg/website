from pymongo import MongoClient
import json

connection = MongoClient()
db = connection['matrix']
yearbook = db.yearbook

with open('test/test_data.json') as f:
    yb = json.load(f)
    #print(yb)
    for elem in yb['data']:
        print("inserted "+ elem['name'])
        yearbook.insert(elem)

print("testing...............")
results = yearbook.find({"batch":2019})
for result in results:
    print(result['roll_no'], " testimonials == ", result['testimonials'])
#
