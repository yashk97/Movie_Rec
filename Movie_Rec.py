from collections import namedtuple
from werkzeug.routing import BaseConverter
from flask import Flask, jsonify, request, session, render_template, redirect, url_for
from get_recommendations import get_recommendations

import random
import bcrypt
import MySQLdb
import numpy as np
app = Flask(__name__)


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


app.url_map.converters['regex'] = RegexConverter

@app.route('/index')
def index():
    if 'uid' in session:
        # print session['email']
        data,pref_list = list_rec()
        # print data
        return render_template('index.html',data=data,gen_list = pref_list)


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
            error = None
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
            print user
            if (user is not None) and bcrypt.checkpw(password,user[4]):
                count = 1
                session['uid'] = user[0]
                session['is_authenticated']=True
                session['pref']=user[5]
                return redirect(url_for('index'))
            else:
                error = "invalid login/password"
                return render_template('login.html',error=error)



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

@app.route('/genre', methods=['GET'])
def list_by_genre():
    db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
    cursor = db.cursor()
    gen = []
    mname = []
    mid = []

    sql = "SELECT * FROM Movie"
    # print sql
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            movie_id = int(row[0])
            movie_name = row[1]
            movie_genre = row[2]
            mid.append(movie_id)
            mname.append(movie_name)
            gen.append(movie_genre)
    except:
        print("Error to fetch data")

    # disconnect from server
    db.close()
    js = []

    d = list(zip(mid, mname, gen))
    # random.shuffle(d)
    mid, mname, gen = zip(*d)
    mid = mid[0:100]
    mname = mname[0:100]
    gen = gen[0:100]
    for a, b, c in zip(mid, mname, gen):
        js1 = {"mid": a, "mname": b, "genre": c}
        js.append(js1)

    return render_template("sort_genre.html",data=js)

def read_ratings():
    Rating = namedtuple("Rating", ["user_id", "movie_id", "rating"])

    db = MySQLdb.connect("localhost","root","root","mov_rec" )
    cursor = db.cursor()
    sql = "SELECT * FROM Rating"
    try:
        # Execute the SQL command
        cursor.execute(sql)
        # Fetch all the rows in a list of lists.
        results = cursor.fetchall()
        for row in results:
            user_id, movie_id, rating = row
            yield Rating(user_id=int(user_id) - 1,
                         movie_id=int(movie_id) - 1,
                         rating=float(rating)
                        )
    except:
        print "Error"


def get_rec_by_genre(genres):
    count = 0
    gen = []
    mname = []
    mid = []

    db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
    cursor = db.cursor()

    sql = "SELECT * FROM Movie WHERE "

    for g in genres:
        if count == 0:
            sql = sql + 'mgenre like "%' + g + '%"'
        else:
            sql = sql + ' or mgenre like "%' + g + '%"'
        count = count + 1
    # print sql
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            movie_id = int(row[0])
            movie_name = row[1]
            movie_genre = row[2]
            mid.append(movie_id)
            mname.append(movie_name)
            gen.append(movie_genre)
    except:
        print("Error to fetch data")

    db.close()
    d = list(zip(mid,mname,gen))
    # random.shuffle(d)
    return d

def list_rec():

    db = MySQLdb.connect("localhost","root","root","mov_rec")
    cursor = db.cursor()
    data = []
    pref_list = []
    sql_num_of_user_ratings = "SELECT count(*) FROM Rating WHERE uid = "+str(session['uid'])
    print sql_num_of_user_ratings
    try:
        cursor.execute(sql_num_of_user_ratings)
        n = cursor.fetchone()[0]
        if n > 0:

            data = get_recommendations(session['uid'])
        else:
            data = None

        genres = session['pref']
        genres = genres.split(" | ")
        pref_list = get_rec_by_genre(genres)
    except:
        print "error"

    js = []
    pref = []
    mid,mname,gen = zip(*data)
    mid = mid[0:100]
    mname = mname[0:100]
    gen = gen[0:100]
    for a,b,c in zip(mid,mname,gen):
        js1 = { "mid" : a, "mname" : b, "genre" : c}
        js.append(js1)

    mid, mname, gen = zip(*pref_list)
    mid = mid[0:100]
    mname = mname[0:100]
    gen = gen[0:100]
    for a, b, c in zip(mid, mname, gen):
        js1 = {"mid": a, "mname": b, "genre": c}
        pref.append(js1)
    return js,pref

@app.route('/edit', methods=['GET'])
def edit_profile():
    # if 'is_authenticated' not in session:
    #     return redirect(url_for('index'))
    # else:
    db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
    cursor = db.cursor()
    uname,age,email="",0,""
    mid,mname,gen=[],[],[]
    pref=""
    sql1 = "select uname,age,email,pref from User where uid="+ str(session['uid'])
    # sql2 = "select * from Movie having mid in (select mid from Rating where uid={0})".format(str(session['uid']))
    # print sql2
    try:
        cursor.execute(sql1)
        row = cursor.fetchone()
        uname= row[0]
        age = row[1]
        email = row[2]
        pref = row[3]

        # cursor.execute(sql2)
        # results = cursor.fetchall()
        # for row in results:
        #     movie_id = int(row[0])
        #     movie_name = row[1]
        #     movie_genre = row[2]
        #     mid.append(movie_id)
        #     mname.append(movie_name)
        #     gen.append(movie_genre)
        # print mid
    except:
        print("Error to fetch data")
    # ratings = {'mid':mid,'mname':mname,'genre':gen}
    data = {'uname':uname, 'age':age, 'email':email, 'pref':pref}#,'ratings':ratings}
    # disconnect from server
    db.close()
    return render_template('edit_profile.html',data=data)

@app.route('/edit', methods=['POST'])
def edit_profile_post():
    if 'is_authenticated' not in session:
        return redirect(url_for('index'))
    else:
        db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
        cursor = db.cursor()
        uname, age = request.form['name'],request.form['age']
        pref = request.form.getlist('pref')

        count = 0
        preferences = ""
        for i in pref:
            if count == 0:
                preferences = preferences + i
            else:
                preferences = preferences + " | " + i
            count += 1
        print preferences
        sql = "Update User set uname='{0}', age={1}, pref='{2}' where uid={3}".format(uname,age,preferences,str(session['uid']))
        print sql
        try:
            cursor.execute(sql)
        except:
            print("Error to fetch data")
        print "update successful"
        # disconnect from server
        db.commit()
        db.close()
        return redirect(url_for('index'))

@app.route('/rating', methods=['GET'])
def rating_list():
    if 'is_authenticated' in session and session['is_authenticated']:
        db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
        cursor = db.cursor()
        gen = []
        mname = []
        mid = []

        sql = "SELECT * FROM Movie"

        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                movie_id = int(row[0])
                movie_name = row[1]
                movie_genre = row[2]
                mid.append(movie_id)
                mname.append(movie_name)
                gen.append(movie_genre)
        except:
            print("Error to fetch data")

        # disconnect from server
        db.close()
        js = []

        d = list(zip(mid, mname, gen))
        # random.shuffle(d)
        mid, mname, gen = zip(*d)
        mid = mid[0:100]
        mname = mname[0:100]
        gen = gen[0:100]
        for a, b, c in zip(mid, mname, gen):
            js1 = {"mid": a, "mname": b, "genre": c}
            js.append(js1)

        return render_template('rating_list.html', data=js)

    else:
        return redirect(url_for('index'))

value = 0

@app.route('/rating/<regex("[0-9]+"):mid>', methods=['GET'])
def getrating(mid):
    if 'is_authenticated' in session and session['is_authenticated']:
        # print mid
        movie_genre,movie_name = "", ""
        global value
        db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
        cursor = db.cursor()
        sql1 = "SELECT * FROM Movie WHERE mid=" + mid
        sql2 = "SELECT rating FROM Rating WHERE mid=" + mid +" and uid="+ str(session['uid'])
        # print sql2
        try:
            cursor.execute(sql1)
            row = cursor.fetchone()
            # print len(row)
            movie_name = row[1]
            movie_genre = row[2].split("|")

            cursor.execute(sql2)
            row = cursor.fetchone()
            # print row
            if row is not None:
                value = int(row[0])
            else:
                value = 0
        except:
            print("Error to fetch data")

        # disconnect from server
        db.close()
        data = { 'mid':mid, 'mname':movie_name, 'mgenre':movie_genre ,'rating':value}
        return render_template('rating.html', data = data)
    else:
        return redirect(url_for('index'))

@app.route('/rating/<regex("[0-9]+"):mid>', methods=['POST'])
def store_rating(mid):
    if 'is_authenticated' in session and session['is_authenticated']:
        print mid
        value = request.form['ratingval']
        db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
        cursor = db.cursor()
        sql1 = "DELETE FROM Rating WHERE uid =" + str(session['uid']) + " and mid = "+ mid
        # print sql1
        sql2 = "INSERT INTO Rating values(" + str(session['uid']) + ", " + mid + ", "+ value +")"
        # print sql2
        try:
            cursor.execute(sql1)
            # print "sql1 done"
            cursor.execute(sql2)
            # print "sql2 done"

        except:
            print()

        # disconnect from server
        db.commit()
        db.close()
        return redirect(url_for('rating_list'))
    else:
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('uid',None)
    session.pop('is_authenticated',None)
    session.pop('pref',None)
    return redirect(url_for('index'))

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000, debug=True)


