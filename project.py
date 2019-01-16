from flask import Flask, render_template, request, \
    redirect, jsonify, url_for, flash


from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from brewery_db_setup import Base, User, Brewery, Beer

from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Seattle Brewery Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///brewery.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except (FlowExchangeError, ValueError)as e:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    if data.get('name') is not None:
        login_session['username'] = data['name']
    else:
        login_session['username'] = data['email']

    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # See if a user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if user_id is not None:
        current_user = getUserInfo(user_id)
        current_user = getUserInfo(user_id)
    else:
        user_id = createUser(login_session)
        current_user = getUserInfo(user_id)

    login_session['user_id'] = current_user.id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;'
    output += 'border-radius: 150px;-webkit-border-radius: 150px;'
    output += '-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])

    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    del login_session['access_token']
    del login_session['gplus_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']

    return redirect(url_for('showBreweries'))


# JSON APIs to view Brewery Information
@app.route('/brewery/<int:brewery_id>/beer/JSON')
def breweryBeerJSON(brewery_id):
    brewery = session.query(Brewery).filter_by(id=brewery_id).one()
    beers = session.query(Beer).filter_by(
        brewery_id=brewery_id).all()
    return jsonify(Beers=[i.serialize for i in beers])


@app.route('/brewery/<int:brewery_id>/beer/<int:beer_id>/JSON')
def beerJSON(brewery_id, beer_id):
    Beer = session.query(Beer).filter_by(id=beer_id).one()
    return jsonify(Beer=Beer.serialize)


@app.route('/brewery/JSON')
def breweriesJSON():
    breweries = session.query(Brewery).all()
    return jsonify(breweries=[r.serialize for r in breweries])


# Show all breweries
@app.route('/')
@app.route('/brewery/')
def showBreweries():
    breweries = session.query(Brewery).order_by(asc(Brewery.name))
    return render_template('breweries.html', breweries=breweries)


# Create a new brewery
@app.route('/brewery/new/', methods=['GET', 'POST'])
def newBrewery():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newBrewery = Brewery(
            name=request.form['name'],
            address=request.form['address'],
            user_id=login_session['user_id'])
        session.add(newBrewery)
        flash('New Brewery %s Successfully Created' % newBrewery.name)
        session.commit()
        return redirect(url_for('showBreweries'))
    else:
        return render_template('newBrewery.html')


# Edit a brewery
@app.route('/brewery/<int:brewery_id>/edit/', methods=['GET', 'POST'])
def editBrewery(brewery_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedBrewery = session.query(
        Brewery).filter_by(id=brewery_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedBrewery.name = request.form['name']
            editedBrewery.address = request.form['address']
            flash('Brewery Successfully Edited %s' % editedBrewery.name)
            return redirect(url_for('showBreweries'))
    else:
        return render_template('editBrewery.html', brewery=editedBrewery)


# Delete a brewery
@app.route('/brewery/<int:brewery_id>/delete/', methods=['GET', 'POST'])
def deleteBrewery(brewery_id):
    if 'username' not in login_session:
        return redirect('/login')
    breweryToDelete = session.query(
        Brewery).filter_by(id=brewery_id).one()
    if request.method == 'POST':
        session.delete(breweryToDelete)
        flash('%s Successfully Deleted' % breweryToDelete.name)
        session.commit()
        return redirect(url_for('showBreweries', brewery_id=brewery_id))
    else:
        return render_template('deleteBrewery.html', brewery=breweryToDelete)

# Show a brewery beer


@app.route('/brewery/<int:brewery_id>/')
@app.route('/brewery/<int:brewery_id>/beer/')
def showBeer(brewery_id):
    brewery = session.query(Brewery).filter_by(id=brewery_id).one()

    user = getUserInfo(brewery.user_id)

    beers = session.query(Beer).filter_by(
        brewery_id=brewery_id).all()
    return render_template(
        'beer.html', beers=beers, brewery=brewery, user=user)


# Create a new beer
@app.route('/brewery/<int:brewery_id>/beer/new/', methods=['GET', 'POST'])
def newBeer(brewery_id):
    if 'username' not in login_session:
        return redirect('/login')
    brewery = session.query(Brewery).filter_by(id=brewery_id).one()
    if request.method == 'POST':
        newBeer = Beer(
            name=request.form['name'],
            description=request.form['description'],
            type=request.form['type'],
            brewery_id=brewery_id, user_id=brewery.user_id)
        session.add(newBeer)
        session.commit()
        flash('New Beer %s Successfully Created' % (newBeer.name))
        return redirect(url_for('showBeer', brewery_id=brewery_id))
    else:
        return render_template('newBeer.html', brewery_id=brewery_id)

# Edit a beer


@app.route(
    '/brewery/<int:brewery_id>/beer/<int:beer_id>/edit',
    methods=['GET', 'POST'])
def editBeer(brewery_id, beer_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedBeer = session.query(Beer).filter_by(id=beer_id).one()
    brewery = session.query(Brewery).filter_by(id=brewery_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedBeer.name = request.form['name']
        if request.form['description']:
            editedBeer.description = request.form['description']
        if request.form['type']:
            editedBeer.price = request.form['type']
        session.add(editedBeer)
        session.commit()
        flash('Beer Successfully Edited')
        return redirect(url_for('showBeer', brewery_id=brewery_id))
    else:
        return render_template(
            'editBeer.html',
            brewery_id=brewery_id,
            beer_id=beer_id, beer=editedBeer)


# Delete a beer
@app.route(
    '/brewery/<int:brewery_id>/beer/<int:beer_id>/delete',
    methods=['GET', 'POST'])
def deleteBeer(brewery_id, beer_id):
    if 'username' not in login_session:
        return redirect('/login')
    brewery = session.query(Brewery).filter_by(id=brewery_id).one()
    beerToDelete = session.query(Beer).filter_by(id=beer_id).one()
    if request.method == 'POST':
        session.delete(beerToDelete)
        session.commit()
        flash('Beer Successfully Deleted')
        return redirect(url_for('showBeer', brewery_id=brewery_id))
    else:
        return render_template('deleteBeer.html', beer=beerToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
