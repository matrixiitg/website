import json
from os import urandom, environ as env
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, session, url_for, request, flash, abort
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode
from pymongo import MongoClient
from datetime import datetime
from flaskext.markdown import Markdown
from bson.objectid import ObjectId
import re

app = Flask(__name__)
app.secret_key = urandom(24)

# Flask Utility to interpret Markdown [Used in html pages with jinja as "{text|markdown}" filter]
Markdown(app)

# OAuth utility Auth0 Used -> https://auth0.com Check it out
oauth = OAuth(app)

######## DB Connections
connection = MongoClient()
# MongoDB DB name: matrix
db = connection['matrix']
# YearBook Collection
# Schema:
# {name, roll_no(int), batch(int), course, testimonials [only .md file ids], titles [not using right now]}
yearbook = db.yearbook
# Testimonials Collection
# Schema:
# {roll_no(int), author_id [LinkedIn Retrieved], author_name, datetime}
testimonials = db.testimonials
# Profiles Collection
# Schema:
# {roll_no(int), id [LinkedIn Retrieved], name, batch(int)}
profiles = db.profiles

######## Setting up Environment Variables -
# We do this so that our code doesn't contain sensitive info and we can easily share it,
# although right now we have exposed it on github,
# which in principle is dangerous and can be exploited by someone else ;P

# CALLBACK_URL = env(['CALLBACK_URL'])
# AUTH0_ID = env(['CLIENT_ID_AUTH0'])
# AUTH0_SECRET = env(['CLIENT_SECRET_AUTH0'])
AUTH0_ID = 'ZY0nrFukhFZYENGZlKus01I8IlhsCzCa'
AUTH0_SECRET = 'ejH_iKscvD91y9l9r_IfiPVkMdNDzW9eGYwFxXK-hVUstceeJSlyL856ERuB1LMY'
CALLBACK_URL = 'http://localhost:5000/callback/'

# AUTH0 API Object, This has all methods required for necessary Auth0 operations
auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_ID,
    client_secret=AUTH0_SECRET,
    api_base_url='https://matrix-iitg.auth0.com',
    access_token_url='https://matrix-iitg.auth0.com/oauth/token',
    authorize_url='https://matrix-iitg.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)


# Function to check if a url function is accessed without login, if it is then redirect to main page
# FOR TESTING PURPOSES IF AUTH0 ISN'T WORKING REMOVE THIS FROM THE CORRESPONDING VIEW AND USE IT DIRECTLY
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            # Redirect to Login page here
            flash('You need to be logged in before accessing this page.')
            return redirect('/')
        return f(*args, **kwargs)

    return decorated


######## Views - Functions that renders html pages

# Basic matrix intro page
@app.route('/')
def index():
    return render_template('index.html')


# Dimension page
@app.route('/dimension/')
def dimension():
    return render_template('dimension.html')


# Team Page
@app.route('/team/')
def team():
    return render_template('team.html')


# Login page
@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=CALLBACK_URL,
                                    audience='https://matrix-iitg.auth0.com/userinfo')


# Callback Page -> After login Auth0 service redirects us here
#  as is mentioned in authorize_redirect function in login view
@app.route('/callback/')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    response = auth0.get('userinfo')
    userinfo = response.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    return redirect(url_for('verification'))


# First time login redirects to verification page where people enter their roll_no and batch
# There's one thing getting both roll_no and batch is actually redundant, roll_no itself is sufficient
@app.route('/verify/', methods=['GET', 'POST'])
def verification():
    if request.method == 'GET':
        try:
            # If this fails it means somebody is accessing this page without getting redirected from login
            user_id = session['profile']['user_id']
        except:
            # So if fails redirect to error page you are at wrong place
            return abort(404)
        # If this person is logging in not for the first time then his user_id must be there in profiles collection
        if profiles.count_documents({'id': user_id}):
            return redirect(url_for('dashboard'))
        # If not then redirect to fill up the form
        else:
            return render_template('verification.html')
    # Request.method is POST hence information is to be submitted
    else:
        # Validate the request parameters
        roll_no = request.form['roll_no']
        batch = request.form['batch']
        # Validation of roll_no & batch by regex match
        if re.match(r'^[0-9][0-9][0-2]1230[0-9][0-9]$', str(roll_no)) and re.match(r'^20[0-9][0-9]$', str(batch)):
            profiles.insert_one({
                "roll_no": int(request.form['roll_no']),
                "id": session['profile']['user_id'],
                "name": session['profile']['name'],
                "batch": int(request.form['batch'])
            })
            return redirect(url_for('dashboard'))
        else:
            flash('Enter Correct information')
            return render_template('verification.html')


# Page wherein one can add his/her profile parameters like BIO etc.
# Now observe since our choice of DB was MongoDB we can actually extend the DB dynamically in future
# Hence can add fields even afterwards without data redundancy/duplication.
@app.route('/update_profile/', methods=['GET', 'POST'])
def update_profile():
    pass
    ## TODO: HTML page + GET POST requests handle karni h


# Final Landing Page after successful login/verification
@app.route('/dashboard/')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))
## TODO: HTML page banana h


# Logout view - redirects to index view
@app.route('/logout')
@requires_auth
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('index', _external=True), 'client_id': AUTH0_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


# Yearbook Pages
@app.route('/yearbook/<batch>/')
@requires_auth
def yearbook_url(batch):
    if batch_validation(batch):
        students = yearbook.find({"batch": int(batch)})
        return render_template('yearbook.html', students=students, batch=batch)
    else:
        # If Batch no is not correct than redirect to error page saying you are at wrong place
        return abort(404)


# Already written Testimonials for a particular person
@app.route('/testimonials/<roll_no>/')
@requires_auth
def testimonials_url(roll_no):
    # fetch testimonials
    if roll_no_validation(roll_no):
        # Finding student record in yearbook collection using roll_no
        student = yearbook.find_one({"roll_no": int(roll_no)})
        testimonial_array = [] # Empty Array
        for id in student['testimonials']:
            # Search testimonial id in testimonials collection
            # Append the markdown file content and fetched information to the empty array we declared above
            result = testimonials.find_one({'_id': ObjectId(id)})
            # Opening markdown file
            with open('markdowns/' + str(id) + '.md', 'r') as md:
                testimonial_array.append({
                    "author_name": result['author_name'],
                    "author_id": result['author_id'],
                    "markdown": md.read(),
                    "date": result['datetime']
                })

        return render_template('testimonials.html', testimonies=testimonial_array, student=student)
    else:
        return abort(404)


# Add testimonial for a particular person
@app.route('/add_testimonial/<roll_no>/', methods=['GET', 'POST'])
@requires_auth
def add_testimonial(roll_no):
    roll_no = int(roll_no)
    if roll_no_validation(roll_no):
        if request.method == 'GET':
            return render_template('add_testimonial.html', roll_no=roll_no)
        else:
            # Insert testimonial in testimonials collection
            result = testimonials.insert_one({
                "roll_no": int(roll_no),
                "author_id": session['profile']['user_id'],
                "author_name": session['profile']['name'],
                "datetime": datetime.now()
            })
            # Retrieve Id of inserted record in mongodb collection,
            # each time we add new entry it is automatically assigned new id
            # Also since Database Technology is smart enough to handle concurrency issues
            # Using this id serves the problem of markdown filesystem concurrent write operations on same file
            testimonial_id = str(result.inserted_id)

            # Write in md file
            with open('markdowns/' + str(testimonial_id) + '.md', 'w') as g:
                g.write(request.form['text'])
            # Add testimonial id to yearbook testimonials array field
            yearbook.update({"roll_no": roll_no}, {"$push": {"testimonials": testimonial_id}})
            # Redirect to that person's testimonials
            return redirect(url_for('testimonials_url', roll_no=roll_no))
    else:
        return abort(404)

# 404 error handler - abort(404) redirects us here
@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404


######## Helper Functions

def roll_no_validation(roll_no):
    # check if roll no is an integer
    try:
        roll_no = int(roll_no)
    except:
        return False  # invalid roll no
    # The method below is really nice since yearbook is manually updated collection
    # So chances of adding testimonial for incorrect roll_no is eliminated
    if yearbook.count_documents({'roll_no': roll_no}) != 0:
        return True
    else:
        return False


def batch_validation(batch):
    # check if roll no is an integer
    try:
        batch = int(batch)
    except:
        pass  # invalid roll no

    # Similarly, The method below is really nice since yearbook is manually updated collection
    # So chances of adding testimonial for incorrect batch is eliminated
    if yearbook.count_documents({'batch': batch}) != 0:
        return True
    else:
        return False

# Turn debug =  False in production
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
