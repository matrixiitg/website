import json
from os import urandom, environ as env

from flask_misaka import Misaka
from werkzeug.exceptions import HTTPException
from functools import wraps
from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, request
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
Misaka(app)
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
        user_id = session['profile']['user_id']
        if profiles.count_documents({'user_id': user_id}):
            redirect(url_for('dashboard'))
        else:
            return render_template('verification.html')
    else:
        # Validate the request parameters and then send to team for review
        pass


@app.route('/callback/')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Check if user is legit
    # maybe ask them their roll no


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
    return auth0.authorize_redirect(redirect_uri="http://127.0.0.1:5000/callback/",
                                    audience='https://matrix-iitg.auth0.com/userinfo')


@app.route('/dashboard')
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
def yearbook_url(batch):
    if batch_validation(batch):
        students = yearbook.find({"batch": int(batch)})
        return render_template('yearbook.html', students=students)
    else:
        pass  # error page


@app.route('/testimonials/<roll_no>/')
def testimonials_url(roll_no):
    # fetch testimonials
    if roll_no_validation(roll_no):
        student = yearbook.find_one({"roll_no": int(roll_no)})
        testimonial_array = []
        for id in student['testimonials']:
            result = testimonials.find_one({'id': id})
            print("id = ",  id)
            with open('markdowns/' + str(id) + '.md', 'r') as y:
                testimonial_array.append({
                    "author_name": result['author_name'],
                    "author_id": result['author_id'],
                    "markdown": y.read(),
                    "date":result['datetime']
                })
                print(y.read())

        return render_template('testimonials.html', testimonies=testimonial_array, student=student)
    else:
        pass  # error page


@app.route('/add_testimonial/<roll_no>/', methods=['GET', 'POST'])
def add_testimonial(roll_no):
    # print(request.form['text'])
    print(roll_no)
    if roll_no_validation(roll_no):
        if request.method == 'GET':
            print("yes")
            return render_template('add_testimonial.html', roll_no=roll_no)
        # rollno validate karna hai
        else:
            # open total_count
            with open('markdowns/total_count', 'r') as f:
                count = f.read()
                count = int(count)
            id = count + 1
            with open('markdowns/' + str(id) + '.md', 'w') as g:
                g.write(request.form['text'])
            with open('markdowns/total_count', 'w') as f:
                f.write(str(id))

            testimonials.insert_one({
                "id": id,
                "roll_no": roll_no,
                # "author_id": session['profile']['user_id'],
                # "author_name": session['profile']['name'],
                "datetime": datetime.now()
            })
            print('gaya tha ')
            yearbook.update_one({"roll_no": roll_no}, {"$push": {"testimonials": id}},upsert = True)



            return redirect(url_for('testimonials_url', roll_no=roll_no))
    else:
        pass  # error page


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
    app.run(debug=True)
