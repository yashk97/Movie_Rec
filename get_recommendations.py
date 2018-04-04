import numpy as np
from math import sqrt
import MySQLdb
from collections import namedtuple
def findmin(sum):
    least = sum[0]      #least element after -1
    leasti = 0
    for i in range(len(sum)):
        if(sum[i]<least and sum[i]!=-1):
            least = sum[i]
            leasti = i

    print "In findmin"
    print least,leasti
    print "exit findmin"
    return leasti


def findmax(sum):
    maxi = 0
    max1 = sum[0]
    for i in range(len(sum)):
        if(sum[i]>max1 and sum[i]!=0):
            max1 = sum[i]
            maxi = i
    return maxi

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
        print "Error in reading ratings"
    db.close()

def get_recommendations(uid):

    ratings = read_ratings()
    db = MySQLdb.connect("localhost","root","root","mov_rec" )
    cursor = db.cursor()

    #getUserLength
    sql = 'SELECT COUNT(*) FROM User'
    cursor.execute(sql)
    userlength = cursor.fetchone()[0]
    print(userlength)

    #getMovieLength
    sql = 'SELECT COUNT(*) FROM Movie'
    cursor.execute(sql)
    movielength = cursor.fetchone()[0]
    print(movielength)
    # disconnect from server


    #--------------------------------------------------------------------
    #GET UVM

    uvm = np.zeros((userlength,movielength))
    for r in ratings:
        uvm[r.user_id][r.movie_id] = r.rating

    #-----------------------------------------------------------------------
    #GET RECOMMENDATION
    lenmovie = movielength
    lenuser = userlength
    sum = np.zeros(lenuser)
    marked1 = np.zeros(lenmovie)
    marked = np.zeros(lenmovie)
    uid -= 1

    #calculate euclidian distance
    for i in range(lenuser):
        if(uid!=i):
            for j in range(lenmovie):
                sum[i] += (uvm[uid][j]-uvm[i][j])*(uvm[uid][j]-uvm[i][j])
        elif uid==i:
            sum[i] = -1

        if sum[i]>=0:
            sum[i] = sqrt(sum[i])
            if sum[i]==0:
                print i
                print(sum[i])

    #print("Negative",sum[uid])
    #find user's closest

    user_closest = findmin(sum)

    print("Recommend",user_closest)

    for j in range(lenmovie):
        if(uvm[user_closest][j] > 0.0):
            # print("In first for",j)
            marked1[j] = 1

    for j in range(lenmovie):
        if(uvm[uid][j] == 0 and marked1[j]):
            marked[j] = uvm[user_closest][j]
            # print(marked[j],j,"In second for")

    #return recommend vector
    # for i in range(len(marked)):
    #     if(marked[i]!=0):
    #         print(marked[i],i,"In third for")


    print("Max",findmax(marked))
    final1 = np.argsort(marked)[::-1][:10]
    r = final1+1

    mname = []
    mgenre = []
    mid = r.tolist()
    try:
        for i in range(len(mid)):
            sql = "SELECT mname,mgenre FROM Movie WHERE mid={0}".format(r[i])
            cursor.execute(sql)
            m = cursor.fetchone()
            m_name = m[0]
            m_genre = m[1]

            mname.append(m_name)
            mgenre.append(m_genre)
    except:
        print "Error in fetching recommended movies"
    db.close()
    d = list(zip(mid, mname, mgenre))
    return d
