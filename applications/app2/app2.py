from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form.get('username')
    return f'<h1>Hello, {username}!</h1><p>Thank you for submitting the form.</p>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)