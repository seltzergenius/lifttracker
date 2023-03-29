from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import date, datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import os

login_manager = LoginManager()
login_manager.login_view = 'login'

Base = declarative_base()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

login_manager.init_app(app)


class User(UserMixin, Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    password = Column(String(256))

class LiftLog(Base):
    __tablename__ = 'liftlog'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    lift = Column(String(100))
    weight = Column(Integer)
    sets = Column(Integer)
    reps = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'))

def sessionfactory():
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_connection = f"mysql+mysqldb://{db_user}:{db_password}@/{'liftlog'}?unix_socket=/cloudsql/liftlog-381914:us-east1:liftlog"
    engine = create_engine(db_connection, echo=True)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = Session()
    return session


@login_manager.user_loader
def load_user(user_id):
    session = sessionfactory()
    user = session.query(User).get(int(user_id))
    session.close()
    return user

def new_entry(user_id, lift, weight, sets, reps, date):
    session = sessionfactory()
    newlift = LiftLog(user_id=user_id, date=date, lift=lift, weight=weight, sets=sets, reps=reps)
    session.add(newlift)
    session.commit()
    session.close()
    
def get_lift_data(user_id):
    session = sessionfactory()
    lift_data = session.query(LiftLog).filter_by(user_id=user_id).order_by(LiftLog.date).all()
    session.close()

    grouped_data = {}
    for lift in lift_data:
        if lift.lift not in grouped_data:
            grouped_data[lift.lift] = {
                'dates': [],
                'weights': []
            }
        grouped_data[lift.lift]['dates'].append(lift.date)
        grouped_data[lift.lift]['weights'].append(lift.weight)

    result = []
    for lift_name, data in grouped_data.items():
        result.append({
            'lift_name': lift_name,
            'dates': data['dates'],
            'weights': data['weights']
        })

    return result

def printlog(user_id):
    session = sessionfactory()
    liftlog = session.query(LiftLog).filter_by(user_id=user_id).all()
    logfile = []
    for lift in liftlog:
        logline = {
            'date': lift.date,
            'lift': lift.lift,
            'weight': lift.weight,
            'sets': lift.sets,
            'reps': lift.reps
           }
        logfile.append(logline)
    session.close()
    return logfile

def cleartable(confirmation):
    if confirmation == "Y":
        session = sessionfactory()
        session.query(LiftLog).delete()
        session.commit()
        session.close()

def liftdashboard(user_id):
    lift_data = get_lift_data(user_id)
    return lift_data

@app.route("/")
@login_required
def main():
    if current_user.is_authenticated:
        user_id = current_user.id
        lift_data = liftdashboard(user_id)
        return render_template('liftdashboard.html', lift_data=lift_data)
    else:
        return redirect(url_for('login'))

@app.route("/addentry", methods=['POST', 'GET'])
@login_required
def addentry():
    if request.method == 'POST':
        data = request.get_json()
        lift = data['lift']
        weight = data['weight']
        reps = data['reps']
        sets = data['sets']
        date_str = data.get('date', None)
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            date_obj = date.today()
        user_id = current_user.id
        new_entry(user_id, lift, weight, reps, sets, date_obj)
        return jsonify({'status': 'success'})
    return render_template('addentry.html')

@app.route("/updateentry", methods=['POST'])
@login_required
def update_entry():
    if request.is_json:
        data = request.get_json()
        date = datetime.strptime(data['date'], "%Y-%m-%d").date()
        lift = data['lift']
        weight = int(data['weight'])
        sets = int(data['sets'])
        reps = int(data['reps'])
        user_id = current_user.id

        # Update the entry in the database
        session = sessionfactory()
        entry = session.query(LiftLog).filter_by(user_id=user_id, date=date, lift=lift).first()
        if entry:
            entry.weight = weight
            entry.sets = sets
            entry.reps = reps
            session.commit()
            session.close()
            return '', 200
        else:
            session.close()
            return 'Entry not found', 400
    else:
        return 'Invalid request', 400

# this was for testing I don't want this live lol

# @app.route("/deletetable", methods=['POST', 'GET'])
# @login_required
# def killtable():
#     if request.method == 'POST':
#         confirmation = request.form['confirmation']
#         if confirmation == "Y":
#             cleartable(confirmation)
#             return redirect(url_for('main'))
#         else:
#             return "Table Not Deleted: You must confirm you really want to delete all data!"
#     return render_template('confirmdelete.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        session = sessionfactory()
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        session.add(new_user)
        session.commit()
        session.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session = sessionfactory()
        username = request.form['username']
        password = request.form['password']
        user = session.query(User).filter_by(username=username).first()
        session.close()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main'))
        else:
            return "Invalid username or password"
    return render_template('login.html')

@app.route('/logs')
@login_required
def logs():
    user_id = current_user.id
    data = printlog(user_id)
    return render_template('logs.html', data=data)

@app.route("/liftcharts")
@login_required
def liftcharts():
    if current_user.is_authenticated:
        user_id = current_user.id
        lift_data = get_lift_data(user_id)
        return render_template('liftcharts.html', lift_data=lift_data)
    else:
        return redirect(url_for('register'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run()