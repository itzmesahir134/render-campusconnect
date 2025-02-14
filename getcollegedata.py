import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request

app = Flask(__name__)

# Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate('/etc/secrets/ServiceAccountKey.json'))

# Get Firestore database reference
db = firestore.client()

def read(state, college_email):
    try:
        if '@' not in college_email:
            return {"error": "Invalid email format"}, 400

        domain = college_email.split('@')[1]

        # Query Firestore with a filter (more efficient)
        query = db.collection(state).where("domain", "==", domain).stream()

        matched_colleges = [doc.to_dict().get("Institution Name") for doc in query]

        return {"colleges": matched_colleges if matched_colleges else ["No colleges found"]}, 200

    except Exception as e:
        return {"error": [str(e)]}, 404

@app.route("/get-colleges/<state>/<college_email>")
def get_data(state, college_email):
    data, status = read(state, college_email)
    return jsonify(data), status

#?collegeHead_email=something@gmail.com&Headpassword=frdfszerg"
#http://127.0.0.1:5000/create-colleges/sahir@gmail.com/Anayah123/SBMP/sbfkebcvkdb/True?collegeHead_email=smit@gmail.com&Headpassword=hihuhnediuwjkch
#/create-colleges/sahir@sbmp.ac.in/Anayah@123/No%20colleges%20found/ZLByMI4dkUa0vBxakiKbxIMCwvD3/true?collegeHead_email=smit@sbmp.ac.in&Headpassword=Pass@12
@app.route("/create-colleges/<college_email>/<password>/<college_name>/<userRef>/<isHead>")
def create_college(college_email, password, college_name, userRef, isHead):
    print(college_email,password,college_name,userRef,isHead)
    if isHead == "True":
        collegeHead_email = request.args.get('collegeHead_email', 'No extra head provided\n')
        collegeHead_password = request.args.get('Headpassword', 'No extra password provided')
        print(collegeHead_email, collegeHead_password)
    else:
        collegeHead_email, password = college_email, collegeHead_password 
        
    return jsonify(college_email,password,college_name,userRef,isHead,collegeHead_email, collegeHead_password), 200

@app.route("/")
def home():
    return "Welcome to College Finder API!"

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 5000))  # Use dynamic port for cloud hosting
    app.run(debug=True, host="0.0.0.0", port=PORT)
