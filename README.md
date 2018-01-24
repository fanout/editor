# Editor

Collaborative editor using operational transformations.

OT algorithms and code based on [Tim Baumann's project](https://github.com/Operational-Transformation).

Client textarea uses CodeMirror.

Server is a Django app. Updates are sent over Fanout Cloud or Pushpin.

There is a public instance available here: [http://editor.fanoutapp.com](http://editor.fanoutapp.com).

## Usage

Install dependencies and setup database:

```sh
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

Note: default storage is sqlite.

### Running with Fanout Cloud

Create a `.env` file containing `GRIP_URL`:

```sh
GRIP_URL=https://api.fanout.io/realm/{realm-id}?iss={realm-id}&key=base64:{realm-key}
```

Be sure to replace `{realm-id}` and `{realm-key}` with the values from the Fanout control panel.

In a separate shell, run ngrok for local tunneling:

```sh
ngrok http 8000
```

In the Fanout control panel, set the ngrok host/port as the Origin Server.

Run a local instance of the project:

```sh
python manage.py runserver
```

Then open up two browser windows to your Fanout Cloud domain (e.g. https://{realm-id}.fanoutcdn.com/). Requests made to Fanout Cloud should be routed through ngrok to the local instance.

### Running with Pushpin

Create a `.env` file containing `GRIP_URL`:

```sh
GRIP_URL=http://localhost:5561
```

Run Pushpin:

```sh
pushpin --route="* localhost:8000"
```

Run the server:

```sh
python manage.py runserver
```

Then open up two browser windows to [http://localhost:7999/](http://localhost:7999/).
