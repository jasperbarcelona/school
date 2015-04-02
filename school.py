import flask, flask.views
from flask import url_for, request, session, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from flask import render_template
from random import randint
from flask.ext import admin
from flask.ext.admin.contrib import sqla
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin import Admin, BaseView, expose
import threading
import requests
import time
from time import sleep
import os
import uuid


app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sgb.db'
db = SQLAlchemy(app)
app.secret_key = '234234rfascasascqweqscasefsdvqwefe2323234dvsv'

API_KEY = 'ecc67d28db284a2fb351d58fe18965f9'
SCHOOL_ID = 1234

SMS_URL = 'https://post.chikka.com/smsapi/request'
CLIENT_ID = 'ef8cf56d44f93b6ee6165a0caa3fe0d1ebeee9b20546998931907edbb266eb72'
SECRET_KEY = 'c4c461cc5aa5f9f89b701bc016a73e9981713be1bf7bb057c875dbfacff86e1d'
SHORT_CODE = '29290420420'
CONNECT_TIMEOUT = 5.0


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_no = db.Column(db.String(20))
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(30))
    middle_name = db.Column(db.String(30))
    level = db.Column(db.Integer)
    department = db.Column(db.String(30))
    section = db.Column(db.String(30))
    parent_contact = db.Column(db.String(12))

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_no = db.Column(db.String(30))
    student_name = db.Column(db.String(60))
    date = db.Column(db.String(20))
    time_in = db.Column(db.String(10))
    time_out = db.Column(db.String(10))
    timestamp = db.Column(db.String(20))


def get_student_data(id_no):
    return Student.query.filter_by(id_no=id_no).first()


# def log_user(id_no):
#     student = get_student_data(id_no)
#     student_name = student.last_name+', '+\
#                    student.first_name+' '+\
#                    student.middle_name[:1]+'.'

#     a = Log(
#         id_no=id_no,
#         student_name=student_name,
#         date=time.strftime("%B %d, %Y"),
#         time_in=time.strftime("%I:%M %p"),
#         timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
#         )

#     db.session.add(a)
#     db.session.commit()

#     return None


# def log_out(id_no):
#     student = get_student_data(id_no)
#     student_name = student.last_name+', '+\
#                    student.first_name+' '+\
#                    student.middle_name[:1]+'.'

#     a = Log.query.filter_by(id_no=id_no).order_by(Log.timestamp.desc()).first()
#     a.time_out = time.strftime("%I:%M %p")
#     db.session.commit()

#     return None


def send_message(id_no, time):
    student = get_student_data(id_no)
    sendThis = 'Good day! Your child, '+student.first_name+' '+\
                student.last_name+' has entered the school gate at '+\
                time+'.'

    message_options = {
            'message_type': 'SEND',
            'message': sendThis,
            'client_id': CLIENT_ID,
            'mobile_number': get_student_data(id_no).parent_contact,
            'secret_key': SECRET_KEY,
            'shortcode': SHORT_CODE,
            'message_id': uuid.uuid4().hex
        }

    sent = False
    while not sent:
        try:
            r = requests.post(
                SMS_URL,
                message_options
                # timeout=(int(CONNECT_TIMEOUT))           
            )
            sent =True
            print r.text

        except requests.exceptions.ConnectionError as e:
            sleep(5)
            print "Too slow Mojo!"
            pass
    
    return None


def send_message_out(id_no, time):
    student = get_student_data(id_no)
    sendThis = 'Good day! Your child, '+student.first_name+' '+student.last_name+\
               ' has exited the school gate at '+time+'.'

    message_options = {
            'message_type': 'SEND',
            'message': sendThis,
            'client_id': CLIENT_ID,
            'mobile_number': get_student_data(id_no).parent_contact,
            'secret_key': SECRET_KEY,
            'shortcode': SHORT_CODE,
            'message_id': uuid.uuid4().hex
        }

    sent = False
    while not sent:
        try:
            r = requests.post(
                SMS_URL,
                message_options
                # timeout=(CONNECT_TIMEOUT)
                
            )
            sent =True
            print r.text

        except requests.exceptions.ConnectionError as e:
            sleep(5)
            print 'Too slow Mojo!'
            pass

    return None


def log_in(id_no, date, time_in,military_time):
    # log = Log.query.filter_by(id_no=id_no).order_by(Log.timestamp.desc()).first()
    student = get_student_data(id_no)
    suffix = get_suffix(student)
    student_name = student.last_name+', '+\
                   student.first_name+' '+\
                   student.middle_name[:1]+'.'

    log_data = {
            'api_key': API_KEY,
            'school_id': SCHOOL_ID,
            'id_no': id_no,
            'name': student_name,
            'level': str(student.level)+suffix,
            'section': student.section,
            'department': student.department,
            'date': date,
            'time_in': time_in,
            'military_time': military_time
        }

    logged=False
    while not logged:
        try:
            l = requests.post(
                'http://sgbadmin.herokuapp.com/addlog',
                log_data
                # timeout=(CONNECT_TIMEOUT)
            )
            logged=True
            print str(l.status_code) + ' log'

        except requests.exceptions.ConnectionError as e:
            sleep(5)
            print 'Too slow Log'
            pass
    
    return None


def log_out(id_no, date, time):

    log_data = {
            'api_key': API_KEY,
            'school_id': SCHOOL_ID,
            'id_no': id_no,
            'date': date,
            'time_out': time
        }

    logged=False
    while not logged:
        try:
            l = requests.post(
                'http://sgbadmin.herokuapp.com/timeout',
                log_data
                # timeout=(CONNECT_TIMEOUT)
            )
            logged=True
            print str(l.status_code) + ' log'

        except requests.exceptions.ConnectionError as e:
            sleep(5)
            print 'Too slow Log'
            pass

    return None


def get_suffix(student):
    if student.department=='faculty':
        suffix=''

    else:
        if student.level==1:
            suffix='st Grade'
        elif student.level==2:
            suffix='nd Grade'
        elif student.level==3:
            suffix='rd Grade'
        else:
            suffix='th Grade'

    return suffix


class IngAdmin(sqla.ModelView):
    column_display_pk = True
admin = Admin(app)
admin.add_view(IngAdmin(Student, db.session))


@app.route('/', methods=['GET', 'POST'])
def index_route():
    session['action'] = 'login'
    session['current_id'] = ''
    return flask.render_template(
        'index.html',
        action=session['action'],
        data="Ready",
        date=time.strftime("%B %d, %Y")
        )


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


@app.route('/login', methods=['GET', 'POST'])
def webhooks_globe():
    id_no = flask.request.form.get("number", "undefined")
    date = time.strftime("%B %d, %Y")
    time_now = time.strftime("%I:%M %p")
    military_time = time.strftime("%H:%M")

    if get_student_data(id_no):
        if session['action']=='logout':
            if session['current_id'] != id_no:
                message_thread = threading.Thread(target=send_message_out,args=[id_no, time_now])    
                message_thread.start()

                log_thread = threading.Thread(target=log_out,args=[id_no, date, time_now,])
                log_thread.start()

        else:
            if session['current_id'] != id_no:
                message_thread = threading.Thread(target=send_message,args=[id_no, time_now])    
                message_thread.start()

                log_thread = threading.Thread(target=log_in,args=[id_no, date, time_now, military_time])
                log_thread.start()

        student = get_student_data(id_no)
        suffix = get_suffix(student)
        session['current_id'] = id_no

        return flask.render_template(
            'info.html',
            action=session['action'],
            data='Sent',
            date=time.strftime("%B %d, %Y"),
            id_no=student.id_no,
            level=str(student.level)+suffix,
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
    a = Student(
        id_no='2011334281',
        first_name='Jasper Oliver', 
        last_name='Barcelona',
        middle_name='Estrada',
        level=2,
        department='student', 
        section='Fidelity',
        parent_contact='639183339068'
        )

    b = Student(
        id_no='2011334282',
        first_name='Prof', 
        last_name='Barcelona', 
        middle_name='Estrada', 
        department='faculty', 
        parent_contact='639183339068'
        )

    db.session.add(a)
    db.session.add(b)
    db.session.commit()
    return 'ok'


if __name__ == '__main__':
    app.debug = True
    app.run()