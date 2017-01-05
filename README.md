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

Then open up two browser windows to [http://localhost:7999/](http://localhost:7999/).
