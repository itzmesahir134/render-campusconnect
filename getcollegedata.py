import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request

app = Flask(__name__)

def createFire(collection_path, data, documentName=False):
    
    # Add the document to Firestore
    if documentName:
        doc_ref = db.collection(collection_path).document(documentName)
    else:
        doc_ref = db.collection(collection_path).document()
    doc_ref.set(data,merge=True)
    return doc_ref


# Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate('/etc/secerts/ServiceAccountKey.json'))

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
#http://127.0.0.1:5000/create-colleges/sahir@sbmp.ac.in/Anayah@123/57480220035/No%20colleges%20found/ZLByMI4dkUa0vBxakiKbxIMCwvD3/true?collegeHead_email=smit@sbmp.ac.in&Headpassword=Pass@12
@app.route("/create-colleges/<college_email>/<password>/<identity_id>/<college_name>/<userRef>/<isHead>")
def create_college(college_email, password, identity_id, college_name, userRef, isHead):
    query = (
    db.collection("Colleges")
        .where("CollegeDomain", "==", college_email.split("@")[1])
        .where("CollegeName", "==", college_name)
        .stream()
    )

    # Check if any documents exist
    if any(query):  # Convert stream to list to evaluate results
        return jsonify({"response": False}), 200
    
    
    if isHead == "true":
        collegeHead_email = request.args.get('collegeHead_email')
        collegeHead_password = request.args.get('Headpassword')
    else:
        collegeHead_email = college_email
        collegeHead_password = password
        
    doc_ref = db.collection('Users').document(userRef)
    doc = doc_ref.get()
    data = doc.to_dict()
    
    #Create College
    college_ref = createFire('Colleges', {
        "MainCollegeHead": collegeHead_email,
        "CollegeDomain": college_email.split('@')[1],
        "CollegeName": college_name
        
        })
    
    #Update User Record
    createFire(f'Users/{userRef}/UserColleges', {
        "Authority": "MainCollegeHead",
        "CollegeEmail": college_email,
        "CollegeDomain": college_email.split('@')[1],
        "CollegeName": college_name,
        "isTeacher": False
        }, college_ref.id)
    
    #Create MainCollegeHead Faculty
    createFire(f'Colleges/{college_ref.id}/Faculty', {
        "Name": data.get("display_name"),
        "UserRef": userRef,
        "UserID": data.get()
    },identity_id)
    #u can access the name by doing doc_ref.id
        
    return jsonify({"response": True}), 200

@app.route("/")
def home():
    return "Welcome to College Finder API!"

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 5000))  # Use dynamic port for cloud hosting
    app.run(debug=True, host="0.0.0.0", port=PORT)
