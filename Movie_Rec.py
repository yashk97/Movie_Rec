import random

from flask import Flask, jsonify, request, json, session, render_template, redirect, url_for
import bcrypt
# from recommend import recommend


import MySQLdb

app = Flask(__name__)

@app.route('/index')
def index():
   if 'email' in session:
       print session['email']
       data = genre(session['pref'])
   # print data
       return render_template('index.html',data=data)
   return render_template('index.html')

@app.route("/login", methods=['GET','POST'])
def login():
    if 'is_authenticated' in session and session['is_authenticated']:
        return redirect(url_for('index'))
    else:
        if request.method == 'GET':
            return render_template('login.html')
        else:
            print("Connected")
            # data2= request.get_json(force=True)
            print "Hi"
            # print data2       #COMMENTED FOR TESTING
            email = request.form["email"]
            print email
            password = request.form["password"]
            count = 0
            db = MySQLdb.connect("localhost","root","root","mov_rec")
            cursor = db.cursor()

            sql = "SELECT * FROM User WHERE email='{0}'".format(email)
            # try:
            cursor.execute(sql)
            user = cursor.fetchone()
            if bcrypt.checkpw(password,user[4]):
                count = 1
                session['uid'] = user[0]
                session['name'] = user[1]
                # session['age'] = user[2]
                session['email']=user[3]
                session['is_authenticated']=True
                session['pref']=user[5]
                return redirect(url_for('index'))

            # except:
            #         print "Error"

            # if(js):
            #     count = 1
            # else:
            #     count = 0
            #
            # #c = {"count" : int(count)}
            return redirect(url_for('index'))



@app.route("/register", methods=['GET','POST'])
def register():
    if 'is_authenticated' in session and session['is_authenticated']:
        return redirect(url_for('index'))
    else:
        if request.method == 'GET':
            return render_template('register.html')
        else:
            print("in register")
            name = request.form["name"]
            email = request.form["email"]
            age = request.form["age"]
            password = request.form["password"]
            pref = request.form.getlist('pref')

            count = 0
            preferences = ""
            for i in pref:
                if count==0:
                    preferences = preferences + i
                else:
                    preferences = preferences +" | " + i
                count += 1
            print preferences
            db = MySQLdb.connect("localhost","root","root","mov_rec")
            cursor = db.cursor()

            hashed_pw = bcrypt.hashpw(password, bcrypt.gensalt(10))
            sql = "SELECT COUNT(*) FROM User"
            cursor.execute(sql)

            count = cursor.fetchone()[0]

            print(count)


            sql = "INSERT INTO User VALUES({0},'{1}',{2},'{3}','{4}','{5}')".format(count+1,str(name),age,str(email),str(hashed_pw), str(preferences))

            print(sql)

            try:
                cursor.execute(sql)
            except MySQLdb.IntegrityError:
                print "This email already exists"
                return jsonify({"count": 0})
            db.commit()
            return redirect(url_for('login'))

# @app.route("/getgenre", methods=['GET', 'POST'])
def genre(genres):
    # data = request.get_json(force=True)
    # pref = data["genre"]
    # print pref
    genres = genres.split(" | ")
    count = 0

    db = MySQLdb.connect("localhost","root","root","mov_rec")
    cursor = db.cursor()
    genre = []
    mname = []
    mid = []

    sql = "SELECT * FROM Movie WHERE "

    for g in genres:
        if count == 0:
            sql = sql + 'mgenre like "%' + g + '%"'
        else:
            sql = sql + ' or mgenre like "%' + g + '%"'
        count = count + 1
    print sql
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            movie_id = int(row[0])
            movie_name = row[1]
            movie_genre = row[2]
            mid.append(movie_id)
            mname.append(movie_name)
            genre.append(movie_genre)
    except:
        print("Error to fetch data")

    # disconnect from server
    db.close()
    js = []


    d = list(zip(mid,mname,genre))
    random.shuffle(d)
    mid,mname,genre = zip(*d)
    mid = mid[0:100]
    mname = mname[0:100]
    genre = genre[0:100]
    for a,b,c in zip(mid,mname,genre):
        js1 = { "mid" : a, "mname" : b, "genre" : c}
        js.append(js1)

    return js

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('uid',None)
    session.pop('name',None)
    session.pop('is_authenticated',None)
    session.pop('pref',None)
    return redirect(url_for('index'))

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000, debug=True)


