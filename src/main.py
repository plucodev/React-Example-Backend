"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from models import db, Person
from flask_jwt_simple import (
    JWTManager, jwt_required, create_jwt, get_jwt_identity
)
import requests
import json

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_CONNECTION_STRING')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)

# Setup the Flask-JWT-Simple extension
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this!
jwt = JWTManager(app)


# Provide a method to create access tokens. The create_jwt()
# function is used to actually generate the token
@app.route('/getdata')
def getdata():
  r = requests.get('http://192.168.10.139:5000/platinum', stream=True)
  for line in r.iter_lines():
    if line:
      return(jsonify.loads(line) )


@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    params = request.get_json()
    username = params.get('username', None)
    email = params.get('password', None)

    if not username:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not email:
        return jsonify({"msg": "Missing email parameter"}), 400

    # if username != 'test' or password != 'test':
    #     return jsonify({"msg": "Bad username or password"}), 401
    usercheck = Person.query.filter_by(username=username, email=email).first()
    if usercheck == None:
        return jsonify({"msg": "Bad username or password"}), 401

    # Identity can be any data that is json serializable
    ret = {'jwt': create_jwt(identity=username)}
    return jsonify(ret), 200


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/person', methods=['POST', 'GET'])
@jwt_required
def handle_person():

    """
    Create person and retrieve all persons
    """

    # POST request
    if request.method == 'POST':
        body = request.get_json()

        if body is None:
            raise APIException("You need to specify the request body as a json object", status_code=400)
        if 'username' not in body:
            raise APIException('You need to specify the username', status_code=400)
        if 'email' not in body:
            raise APIException('You need to specify the email', status_code=400)

        user1 = Person(username=body['username'], email=body['email'])
        db.session.add(user1)
        db.session.commit()
        return "ok", 200

    # GET request
    if request.method == 'GET':
        all_people = Person.query.all()
        all_people = list(map(lambda x: x.serialize(), all_people))
        return jsonify(all_people), 200

    return "Invalid Method", 404


@app.route('/person/<int:person_id>', methods=['PUT', 'GET', 'DELETE'])
def get_single_person(person_id):
    """
    Single person
    """

    # PUT request
    if request.method == 'PUT':
        body = request.get_json()
        if body is None:
            raise APIException("You need to specify the request body as a json object", status_code=400)

        user1 = Person.query.get(person_id)
        if user1 is None:
            raise APIException('User not found', status_code=404)

        if "username" in body:
            user1.username = body["username"]
        if "email" in body:
            user1.email = body["email"]
        db.session.commit()

        return jsonify(user1.serialize()), 200

    # GET request
    if request.method == 'GET':
        user1 = Person.query.get(person_id)
        if user1 is None:
            raise APIException('User not found', status_code=404)
        return jsonify(user1.serialize()), 200

    # DELETE request
    if request.method == 'DELETE':
        user1 = Person.query.get(person_id)
        if user1 is None:
            raise APIException('User not found', status_code=404)
        db.session.delete(user1)
        db.session.commit()
        return "ok", 200

    return "Invalid Method", 404


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, threaded=True)
