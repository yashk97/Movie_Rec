from __future__ import print_function
from flask import Flask, jsonify, request, json
# from recommend import recommend


import MySQLdb

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello"

@app.route("/getgenre", methods=['GET', 'POST'])
def adventure():
    data = request.get_json(force=True)      #COMMENTED FOR TESTING
    g = data["genre"]
    print(g)
    db = MySQLdb.connect("localhost","root","root","mov_rec")
    cursor = db.cursor()
    genre = []
    mname = []
    mid = []

    sql = "SELECT * FROM Movie WHERE mgenre LIKE '%{0}%'".format(g)

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

    mid = mid[0:100]
    mname = mname[0:100]
    genre = genre[0:100]


    for a,b,c in zip(mid,mname,genre):
        js1 = { "mid" : a, "mname" : b, "genre" : c}
        js.append(js1)

    hi = { "list" : js}
    return jsonify(hi)


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8000, debug=True)
