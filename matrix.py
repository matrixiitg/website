import json
from os import urandom, environ as env

from werkzeug.exceptions import HTTPException
from functools import wraps
from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, request, flash, abort
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode
from pymongo import MongoClient
from datetime import datetime
from flaskext.markdown import Markdown
from bson.objectid import ObjectId
import re

app = Flask(__name__)
# Misaka(app)
Markdown(app)
oauth = OAuth(app)
app.secret_key = urandom(24)

# DB Connections
connection = MongoClient()
db = connection['matrix']
yearbook = db.yearbook
testimonials = db.testimonials
profiles = db.profiles
#
# LINKEDIN_ID = env(['CLIENT_ID_LINKEDIN'])
# LINKEDIN_SECRET = env(['CLIENT_SECRET_LINKEDIN'])
# CALLBACK_URL = env(['CALLBACK_URL'])
#
# AUTH0_ID = env(['CLIENT_ID_AUTH0'])
# AUTH0_SECRET = env(['CLIENT_SECRET_AUTH0'])
AUTH0_SECRET = 'ejH_iKscvD91y9l9r_IfiPVkMdNDzW9eGYwFxXK-hVUstceeJSlyL856ERuB1LMY'
CALLBACK_URL = 'http://localhost:5000/callback/'

auth0 = oauth.register(
    'auth0',
    client_id='ZY0nrFukhFZYENGZlKus01I8IlhsCzCa',
    client_secret=AUTH0_SECRET,
    api_base_url='https://matrix-iitg.auth0.com',
    access_token_url='https://matrix-iitg.auth0.com/oauth/token',
    authorize_url='https://matrix-iitg.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)


# Connect to mongoDB
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            # Redirect to Login page here
            flash('You need to be logged in before accessing this page.')
            return redirect('/')
        return f(*args, **kwargs)

    return decorated


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dimension/')
def dimension():
    return render_template('dimension.html')


@app.route('/team/')
def team():
    return render_template('team.html')


@app.route('/verify/', methods=['GET', 'POST'])
def verification():
    if request.method == 'GET':
        try:
             user_id = session['profile']['user_id']
             print(user_id)
        except:
            # return render_template('verification.html')
            return abort(404)
        if profiles.count_documents({'id': user_id}):
            return redirect(url_for('dashboard'))
        else:
            return render_template('verification.html')
    else:
        # Validate the request parameters and then send to team for review
        # Validation of roll_no regex match | Batch year
        roll_no = request.form['roll_no']
        batch = request.form['batch']
        if re.match(r'^[0-9][0-9][0-2]1230[0-9][0-9]$', str(roll_no)) and re.match(r'^20[0-9][0-9]$', str(batch)):
            profiles.insert_one({
                "roll_no": int(request.form['roll_no']),
                "id": session['profile']['user_id'],
                "name": session['profile']['name'],
                "batch" : int(request.form['batch'])
            })
            return redirect(url_for('dashboard'))
        else:
            flash('Enter Correct information')
            return render_template('verification.html')


@app.route('/update_profile/', methods=['GET', 'POST'])
def update_profile():
    pass
    ##TODO


@app.route('/callback/')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    return redirect(url_for('verification'))


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri="http://172.16.68.63:5000/callback/",
                                    audience='https://matrix-iitg.auth0.com/userinfo')


@app.route('/dashboard/')
@requires_auth
def dashboard():
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))


@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('index', _external=True), 'client_id': 'ZY0nrFukhFZYENGZlKus01I8IlhsCzCa'}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))


@app.route('/yearbook/<batch>/')
@requires_auth
def yearbook_url(batch):
    if batch_validation(batch):
        students = yearbook.find({"batch": int(batch)})
        return render_template('yearbook.html', students=students, batch = batch)
    else:
        return abort(404)

@app.route('/testimonials/<roll_no>/')
@requires_auth
def testimonials_url(roll_no):
    # fetch testimonials
    if roll_no_validation(roll_no):
        student = yearbook.find_one({"roll_no": int(roll_no)})
        testimonial_array = []
        for id in student['testimonials']:
            result = testimonials.find_one({'_id': ObjectId(id) })
            with open('markdowns/' + str(id) + '.md', 'r') as y:
                testimonial_array.append({
                    "author_name": result['author_name'],
                    "author_id": result['author_id'],
                    "markdown": y.read(),
                    "date": result['datetime']
                })

        return render_template('testimonials.html', testimonies=testimonial_array, student=student)
    else:
        return abort(404)


@app.route('/add_testimonial/<roll_no>/', methods=['GET', 'POST'])
@requires_auth
def add_testimonial(roll_no):
    # print(request.form['text'])
    print(roll_no)
    if roll_no_validation(roll_no):
        if request.method == 'GET':
            return render_template('add_testimonial.html', roll_no=roll_no)
        # rollno validate karna hai
        else:
            result = testimonials.insert_one({
                "roll_no": int(roll_no),
                "author_id": session['profile']['user_id'],
                "author_name": session['profile']['name'],
                "datetime": datetime.now()
            })
            id = str(result.inserted_id)

            with open('markdowns/' + str(id) + '.md', 'w') as g:
                g.write(request.form['text'])

            roll_no = int(roll_no)
            yearbook.update({"roll_no": roll_no}, {"$push": {"testimonials": id}})

            return redirect(url_for('testimonials_url', roll_no=roll_no))
    else:
        return abort(404)

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

def roll_no_validation(roll_no):
    # check if roll no is an integer
    try:
        roll_no = int(roll_no)
    except:
        return False  # invalid roll no

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

    if yearbook.count_documents({'batch': batch}) != 0:
        return True
    else:
        return False


if __name__ == '__main__':
    app.run(host = '0.0.0.0', debug=True)
