# import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from datetime import date, datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
app = Flask(__name__)

class LiftLog(Base):

    __tablename__ = 'liftlog'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    lift = Column(String)
    weight = Column(Integer)
    sets = Column(Integer)
    reps = Column(Integer)

def sessionfactory():
    engine = create_engine('sqlite:///lifttracker.db')
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = Session()
    return session

def new_entry(lift, weight, sets, reps, date):
    session = sessionfactory()
    newlift = LiftLog(date=date, lift=lift, weight=weight, sets=sets, reps=reps)
    session.add(newlift)
    session.commit()
    session.close()
    
def printlog():
    session = sessionfactory()
    liftlog = session.query(LiftLog).all()
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

@app.route("/")
def main():
    data = printlog()
    return render_template('index.html', data=data)

@app.route("/addentry", methods=['POST', 'GET'])
def addentry():
    if request.method == 'POST':
        lift = request.form['lift']
        weight = request.form['weight']
        reps = request.form['reps']
        sets = request.form['sets']
        date_str = request.form.get('date', None)
        if date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            date_obj = date.today()
        new_entry(lift, weight, reps, sets, date_obj)
        return redirect(url_for('main'))
    return render_template('addentry.html')

@app.route("/deletetable", methods=['POST', 'GET'])
def killtable():
    if request.method == 'POST':
        confirmation = request.form['confirmation']
        if confirmation == "Y":
            cleartable(confirmation)
            return redirect(url_for('main'))
        else:
            return "Table Not Deleted: You must confirm you really want to delete all data!"
    return render_template('confirmdelete.html')


if __name__ == "__main__":
    app.run()