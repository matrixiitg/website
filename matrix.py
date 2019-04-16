from flask import Flask, request, render_template,redirect

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dimension')
def dimension():
    return render_template('dimension.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/events')
def events():
    return render_template('events.html')

@app.route('/events/')
def event():
    return redirect("/events", code=302)

@app.route('/dimension/gallery')
def dim_gallery():
    return render_template('dim_gallery.html')


if __name__ == '__main__':
    app.run()
