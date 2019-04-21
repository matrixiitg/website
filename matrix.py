import json
from os import urandom, environ as env
from werkzeug.exceptions import HTTPException
from functools import wraps
from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, request
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode
from pymongo import MongoClient

app = Flask(__name__)
oauth = OAuth(app)
app.secret_key = urandom(24)
connection = MongoClient()
db = connection['matrix']
yearbook = db.yearbook
testimonials = db.testimonials
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



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dimension')
def dimension():
    return render_template('dimension.html')


@app.route('/team')
def team():
    return render_template('team.html')


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
    return redirect('/dashboard')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri="http://127.0.0.1:5000/callback/",
                                    audience='https://matrix-iitg.auth0.com/userinfo')


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            # Redirect to Login page here
            return redirect('/')
        return f(*args, **kwargs)

    return decorated


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
    # yb_db = mongo_client['matrix']['yearbook']
    # testimonial_db = mongo_client['matrix']['testimonials']
    print("yo")
    students = yearbook.find({"batch": int(batch)})
    #print(list(students))
    testimonials = {}
    # for student in students:
    #     testimonials[student['roll_no']] = []
    #     for testimonial_id in student['testimonial_ids']:
    #         testimonials[student['roll_no']] = testimonial_db.find(testimonial_id)
    # Random Number generation


    return render_template('yearbook.html', students=students, testimonials=testimonials)


@app.route('/testimonials/<roll_no>')
def testimonials(roll_no):
    #fetch testimonials
    student = yearbook.find_one({"roll_no": int(roll_no)})
    testimonial_array = []
    for id in student['testimonials']:
        result = testimonials.find_one({'id':id})
        with open('markdowns/' + str(id) + '.md', 'r') as y:
            testimonial_array.append({
                "author_name": result['author_name'],
                "author_id": result['author_id'],
                "markdown": y.read()
            })
    return render_template('testimonials.html', testimonies = testimonial_array)


@app.route('/add_testimonial/<roll_no>', methods=['GET', 'POST'])
def add_testimonial(roll_no):
    # print(request.form['text'])
    if request.method == 'GET':
        return render_template('add_testimonials.html', roll_no=roll_no)
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
            f.write(str(id + 1))

        testimonials.insert_one({
            "id": id,
            "roll_no": roll_no,
            "author_id": session['profile']['user_id'],
            "author_name": session['profile']['name'],
        })

        yearbook.update_one({"roll_no": roll_no},{'$push': { 'testimonials': id }})

        return redirect(url_for('testimonials',roll_no=roll_no))



        # write a new file with request.form['text']
        # database mein iska relative address daaldenge
        # jis bande ka daala h uske testimonials pe chale jao

    # @app.route('/add_testimonial', method=['GET', 'POST'])
    # @requires_auth
    # def add_testimonial():
    #     if request.method == 'POST':
    #
    #     else:
    #         return render_template('add_testimonial.html', req = request)


    # @app.route('/auth/linkedin/callback')
    # def auth(response, status, headers):
    #     #verify csrf - headers['state']
    #     if headers['code']:
    #         #continue auth
    #
    #         url = "https://www.linkedin.com/oauth/v2/access_token"
    #
    #         querystring = {"grant_type": "authorization_code", "code": headers['code'], "redirect_uri": "",
    #                        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    #
    #         headers = {
    #             'content-type': "application/x-www-form-urlencoded",
    #             'cache-control': "no-cache",
    #             'postman-token': "28b4a0cc-2822-ae4e-7ed5-5968810b8894"
    #         }
    #
    #         response = requests.request("POST", url, headers=headers, params=querystring) #json contains access_token expires_in
    #         json
    #
    #     else:
    #         #error page
    #         error = headers['error'] # Either 'user_cancelled_login' or 'user_cancelled_authorize'
    #         desc = headers['error_description']



if __name__ == '__main__':
    app.run(debug=True)
