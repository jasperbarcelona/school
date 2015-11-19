import os
import flask, flask.views
from flask import url_for, request, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean
from flask import render_template
from random import randint
from flask.ext import admin
from flask.ext.admin.contrib import sqla
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin import Admin, BaseView, expose
from progressbar import ProgressBar
import datetime
import threading
from threading import Timer
import requests
import time
from time import sleep
import json
import uuid
import sys


app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sgb.db'
db = SQLAlchemy(app)
app.secret_key = '234234rfascasascqweqscasefsdvqwefe2323234dvsv'

LOG_URL = 'http://projectraven.herokuapp.com/addlog'
SCHED_URL = 'http://127.0.0.1:5000/sched/get'
SYNC_URL = 'http://projectraven.herokuapp.com/sync'
API_KEY = 'ecc67d28db284a2fb351d58fe18965f9'

SCHOOL_ID = '1234'
CONNECT_TIMEOUT = 5.0

IPP_URL = 'https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests'
CHIKKA_URL = 'https://post.chikka.com/smsapi/request'

CLIENT_ID = 'ef8cf56d44f93b6ee6165a0caa3fe0d1ebeee9b20546998931907edbb266eb72'
SECRET_KEY = 'c4c461cc5aa5f9f89b701bc016a73e9981713be1bf7bb057c875dbfacff86e1d'
SHORT_CODE = '29290420420'


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_no = db.Column(db.String(20))
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(30))
    middle_name = db.Column(db.String(30))
    level = db.Column(db.String(10), default='None')
    department = db.Column(db.String(30))
    section = db.Column(db.String(30), default='None')
    parent_contact = db.Column(db.String(12))
    modem = db.Column(db.String(2))

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_no = db.Column(db.String(20))
    name = db.Column(db.String(60))
    level = db.Column(db.String(10))
    section = db.Column(db.String(30))
    department = db.Column(db.String(30))
    date = db.Column(db.String(20))
    time = db.Column(db.String(10))
    timestamp = db.Column(db.String(50))
    synced = db.Column(Boolean, unique=False)

class ravenAdmin(sqla.ModelView):
    column_display_pk = True
    can_edit = False
    can_delete = False
    can_create = False

admin = Admin(app, name='Scuola Gesu Bambino', template_mode='bootstrap3')
admin.add_view(ravenAdmin(Student, db.session))
admin.add_view(ravenAdmin(Log, db.session))


def get_student_data(id_no):
    return Student.query.filter_by(id_no=id_no).first()


def log(id_no, date, time):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')

    student = get_student_data(id_no)
    student_name = student.last_name+', '+\
                   student.first_name+' '+\
                   student.middle_name[:1]+'.'

    log_item = Log(
        id_no=id_no,
        name=student_name,
        level=student.level,
        section=student.section,
        department=student.department,
        date=date,
        time=time,
        timestamp=timestamp,
        synced=False
        )

    db.session.add(log_item)
    db.session.commit()

    sync_to_cloud(student,student_name,date,time,timestamp)


def sync_to_cloud(student,name,date,time,timestamp):
    log_data = {
            'api_key': API_KEY,
            'school_id': SCHOOL_ID,
            'id_no': student.id_no,
            'name': name,
            'level': student.level,
            'section': student.section,
            'department': student.department,
            'date': date,
            'time': time,
            'timestamp': timestamp
        }

    attempts = 0
    while attempts < 3:
        try:
            l = requests.post(
                LOG_URL,
                log_data
                # timeout=(CONNECT_TIMEOUT)
            )
            attempts = 3
            print str(l.status_code) + ' log'
            if l.status_code == 201:
                log = Log.query.filter_by(date=date,id_no=student.id_no).order_by(Log.timestamp.desc()).first()
                log.synced = True
                db.session.commit()
                resp = l.json()
                send_sms(name,student.parent_contact,resp['action'],time)

        except requests.exceptions.ConnectionError as e:
            attempts += 1
            print 'Too slow Log'
            sleep(5)


def send_sms(student_name,msisdn,action,time):
    message = 'Good day! We would like to inform you that '+student_name+' has '+action+' the campus at '+time+'.'

    #USE THIS WHEN CONNECTING TO IPP
    # message_options = {
    #         "message": message,
    #         "address": msisdn,
    #         "access_token": 'Os-vcHVaxj6yQrjefuU4Z20tIkzyHxXom_AvK1GfLl0'
    #     }
    # sent = False
    # while not sent:
    #     try:
    #         r = requests.post(
    #         IPP_URL % SHORT_CODE,
    #         params=message_options
    #         )
    #         sent = True
    #         print r.status_code

    #     except requests.exceptions.ConnectionError as e:
    #         print "Sending Failed!"
    #         sleep(5)


    #USE THIS WHEN CONNECTING TO CHIKKA
    message_options = {
            'message_type': 'SEND',
            'message': message,
            'client_id': CLIENT_ID,
            'mobile_number': msisdn,
            'secret_key': SECRET_KEY,
            'shortcode': SHORT_CODE,
            'message_id': uuid.uuid4().hex
        }
    sent = False
    while not sent:
        try:
            r = requests.post(
            CHIKKA_URL,
            message_options
            )
            sent = True
            print r.status_code

        except requests.exceptions.ConnectionError as e:
            print "Sending Failed!"
            sleep(5)


def fetch_records():
    print 'Fetching data from %s...' %SYNC_URL
    params = {'school_id': SCHOOL_ID}

    try:
        g = requests.get(SYNC_URL,params=params)
        resp = g.json()
        print 'Total Records: ' + str(len(resp['Records']))
        return save_records(resp)

    except requests.exceptions.ConnectionError as e:
        print 'An error occurred, could not FETCH records.'
        return('', 500)


def save_records(resp):
    pbar = ProgressBar()
    print 'Saving records to database...'
    try:
        for i in pbar(resp['Records']):
            insert = Student(
                id_no=i['id_no'],
                first_name=i['first_name'],
                last_name=i['last_name'],
                middle_name=i['middle_name'],
                level=i['level'],
                department=i['department'],
                section=i['section'],
                parent_contact=i['parent_contact'],
                )
            db.session.add(insert)
        db.session.commit()
        return('Success',201)

    except requests.exceptions.ConnectionError as e:
        print 'An error occurred, could not SAVE records.'
        return('', 500)


def mark_morning_absent():
    school_info = {
            'api_key': API_KEY,
            'school_id': SCHOOL_ID,
        }

    logged=False
    while not logged:
        try:
            l = requests.post(
                'http://127.0.0.1:5000/absent/morning/mark',
                school_info
                # timeout=(CONNECT_TIMEOUT)
            )
            logged=True
            print str(l.status_code) + ' marked'

        except requests.exceptions.ConnectionError as e:
            sleep(5)
            print 'Too slow mark'
            pass


def mark_afternoon_absent():
    print 'marking.....'
    school_info = {
            'api_key': API_KEY,
            'school_id': SCHOOL_ID,
        }

    try:
        l = requests.post(
            'http://127.0.0.1:5000/absent/afternoon/mark',
            school_info
            # timeout=(CONNECT_TIMEOUT)
        )
        print str(l.status_code) + ' marked'

    except requests.exceptions.ConnectionError as e:
        sleep(5)
        print 'Too slow mark'


def start_morning_timer(time):
    x = datetime.datetime.now()
    y = x.replace(hour=int(time[:2])+1, minute=int(time[3:]), second=0, microsecond=0)
    delta_t = y - x
    secs = delta_t.seconds + 1
    t = Timer(secs, mark_morning_absent)
    t.start()
    print 'time until mark_morning_absent: ' + str(secs/60) + ' min/s'


def start_afternoon_timer(time):
    a = datetime.datetime.now()
    b = a.replace(hour=int(time[:2])+1, minute=int(time[3:]), second=0, microsecond=0)
    delta_c = b - a
    seconds = delta_c.seconds + 1
    c = Timer(seconds, mark_afternoon_absent)
    c.start()
    print 'time until mark_afternoon_absent: ' + str(seconds/60) + ' min/s'
    

def get_schedule():
    try:
        params = {'api_key': API_KEY}
        get_sched = requests.get(SCHED_URL,params=params)
        schedule = get_sched.json()
        start_morning_timer(schedule['morning_time'])
        start_afternoon_timer(schedule['afternoon_time'])

    except requests.exceptions.ConnectionError as e:
        print 'Server is offline, using last schedule synced'
        


@app.route('/', methods=['GET', 'POST'])
def index_route():
    get_schedule()
    session['action'] = 'login'
    session['current_id'] = ''
    return flask.render_template(
        'index.html',
        action=session['action'],
        data="Ready",
        date=time.strftime("%B %d, %Y")
        )


@app.route('/test', methods=['GET', 'POST'])
def test():
    print 'working!'


@app.route('/action', methods=['GET', 'POST'])
def change_action():
    session['current_id'] = ''
    session['action'] = flask.request.args.get('action')
    return flask.render_template(
        'index.html',
        action=session['action'],
        data="Ready",
        date=time.strftime("%B %d, %Y")
        )


@app.route('/sync', methods=['GET', 'POST'])
def sync_database():
    db.drop_all()
    db.create_all()
    return fetch_records()


@app.route('/login', methods=['GET', 'POST'])
def webhooks_globe():
    id_no = flask.request.form.get("number", "undefined")
    date = time.strftime("%B %d, %Y")
    time_now = time.strftime("%I:%M %p")

    if get_student_data(id_no):
        if session['current_id'] != id_no:
            log_thread = threading.Thread(target=log,args=[id_no, date, time_now])
            log_thread.start()

        student = get_student_data(id_no)
        session['current_id'] = id_no

        return flask.render_template(
            'info.html',
            action=session['action'],
            data='Sent',
            date=time.strftime("%B %d, %Y"),
            id_no=student.id_no,
            level=str(student.level),
            section=student.section,
            student_name=student.last_name+', '+\
                         student.first_name+' '+\
                         student.middle_name[:1]+'.'
            )

    return flask.render_template('error.html')



@app.route('/db/rebuild')
def db_rebuild():
    db.drop_all()
    db.create_all()
    # a = Student(
    #     id_no='2011334281',
    #     first_name='Jasper Oliver', 
    #     last_name='Barcelona',
    #     middle_name='Estrada',
    #     level=2,
    #     department='student', 
    #     section='Fidelity',
    #     parent_contact='639183339068'
    #     )

    # b = Student(
    #     id_no='2011334282',
    #     first_name='Prof', 
    #     last_name='Barcelona', 
    #     middle_name='Estrada', 
    #     department='faculty', 
    #     parent_contact='639183339068'
    #     )

    # db.session.add(a)
    # db.session.add(b)
    # db.session.commit()
    return 'ok'


if __name__ == '__main__':
    app.debug = True
    app.run(port=8000)