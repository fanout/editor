# Editor

Collaborative editor using operational transformations.

OT algorithms and code based on [Tim Baumann's project](https://github.com/Operational-Transformation).

Client textarea uses CodeMirror.

Server is a Django app. Updates are sent over Pushpin.

## Usage

Setup, from the base dir:

```sh
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
echo GRIP_URL=http://localhost:5561 > .env
```

Note: default storage is sqlite.

Run Pushpin:

```sh
pushpin --route="* localhost:8000"
```

Run the server:

```sh
python manage.py runserver
```

Create a couple of users:

```sh
curl -d name=alice http://localhost:8000/users/
curl -d name=bob http://localhost:8000/users/
```

Then open up two browser windows, and set `user-id` in the query string. E.g. http://localhost:7999/?user-id=1 and http://localhost:7999/?user-id=2
