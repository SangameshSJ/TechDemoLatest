from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>Application 1</h1><p>This is deployed in subnet 1</p>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)