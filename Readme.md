# Steps to run mock site locally
1. Install requirements:
```
sudo -H pip3 install -r requirements.txt [If installing on python global environment]
pip3 install -r requirements.txt [If in virtual environment]
```

2. Install MongoDB
Follow steps at https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/

3. Start MongoDB
```
$ mongo
$> use matrix
$> db.createCollection('testimonials')
$> db.createCollection('profiles')
$> db.createCollection('yearbook')
$> exit
```

4. Collection are created, for testing you can load test data on yearbook by running test/pymongo_import.py script
```
$ python3 test/pymongo_import.py
```

5. Runserver & Enjoy
```
$ python3 matrix.py
```


