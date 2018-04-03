from collections import namedtuple, defaultdict

from sklearn.neighbors import NearestNeighbors
from werkzeug.routing import BaseConverter
from flask import Flask, jsonify, request, session, render_template, redirect, url_for
import random
import scipy.sparse as sp
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
    if 'email' in session:
        # print session['email']
        data = list_rec()
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
                session['email']=user[3]
                session['is_authenticated']=True
                session['pref']=user[5]
                return redirect(url_for('index'))

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
    random.shuffle(d)
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


def create_training_sets(ratings, n_training, n_testing, user):
    print "Creating user movie-interaction lists"

    user_interactions = defaultdict(set)
    max_movie_id = 0
    for r in ratings:
        user_interactions[r.user_id].add(r.movie_id)
        max_movie_id = max(max_movie_id, r.movie_id)

    # print sorted(user_interactions[530])
    user_interactions = list(user_interactions.values())
    # print len(user_interactions),len()
    sampled_indices =range(len(user_interactions)) #random.sample(xrange(len(user_interactions)), n_training + n_testing)
    # print sorted(sampled_indices), user
    sampled_indices.remove(user)

    users = []
    movies = []
    interactions = []
    for new_user_id, idx in enumerate(sampled_indices):
        users.extend([new_user_id] * len(user_interactions[idx]))
        movies.extend(user_interactions[idx])
        interactions.extend([1.] * len(user_interactions[idx]))

    n_movies = max_movie_id + 1
    training_matrix = sp.coo_matrix((interactions, (users, movies)),
                               shape=(n_training, n_movies)).tocsr()

    users = []
    movies = []
    interactions = []
    users.extend([0] * len(user_interactions[user]))
    movies.extend(user_interactions[user])
    interactions.extend([1.] * len(user_interactions[user]))

    n_movies = max_movie_id + 1
    testing_matrix = sp.coo_matrix((interactions, (users, movies)),
                               shape=(n_testing, n_movies)).tocsr()

    return training_matrix, testing_matrix

def get_recommendations(training, testing):
    knn = NearestNeighbors(metric='euclidean', algorithm="brute")
    knn.fit(training)
    user = testing.toarray()
    others = training.toarray()
    neighbors = knn.kneighbors(user, n_neighbors=10, return_distance=False)
    print neighbors
    db = MySQLdb.connect("localhost", "root", "root", "mov_rec")
    cursor = db.cursor()
    for neighbor in neighbors[0]:
        rec_mov = np.where(np.logical_and(np.invert(user == 1), others[neighbor]))[1] + 1
        format_strings = ','.join(['%s'] * len(rec_mov))
        cursor.execute("SELECT * FROM Movie WHERE mid IN (%s)" % format_strings, tuple(rec_mov))


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
    return random.shuffle(d)

def list_rec():

    db = MySQLdb.connect("localhost","root","root","mov_rec")
    cursor = db.cursor()
    d = []
    sql_num_of_user_ratings = "SELECT count(*) FROM Rating WHERE uid = {}", format(str(session['uid']))
    sql_total_ratings = "SELECT count(*) FROM Rating"
    try:
        cursor.execute(sql_total_ratings)
        total_ratings = cursor.fetchone()

        cursor.execute(sql_num_of_user_ratings)
        n = cursor.fetchone()
        if n > 0:
            ratings = read_ratings()

            training, testing = create_training_sets(ratings, total_ratings, 1, session['uid'])

            get_recommendations(training,testing)
        else:
            genres = session['pref']
            genres = genres.split(" | ")
            d = get_rec_by_genre(genres)
    except:
        print "error"

    js = []



    mid,mname,gen = zip(*d)
    mid = mid[0:100]
    mname = mname[0:100]
    gen = gen[0:100]
    for a,b,c in zip(mid,mname,gen):
        js1 = { "mid" : a, "mname" : b, "genre" : c}
        js.append(js1)

    return js

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
        uname, age= request.form['name'],request.form['age']
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
        random.shuffle(d)
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
    session.pop('email', None)
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


