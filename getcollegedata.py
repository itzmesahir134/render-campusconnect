#localhost:3000/get-colleges/<state>/<college_email>
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
app = Flask(__name__)

    
# Initialize Firebase Admin SDK
cred = credentials.Certificate('/etc/secrets/key.json')  # Replace with your key
firebase_admin.initialize_app(cred)

# Get Firestore database reference
db = firestore.client()

def read(state, college_email):
    print(state,' : ',college_email)
    try:
        if '@' not in college_email:
            return({'error': "invalid email format"}, 400)

        domain = college_email.split('@')[1]

        matched_colleges = []

        doc_ref = db.collection(state)
        query = doc_ref.stream()

        for doc in query:
            data = doc.to_dict()
            if 'domain' in data and data['domain'] == domain:
                matched_colleges.append(data['Institution Name'])
            
        if not matched_colleges:
            return {"error":"no colleges found"}, 404
        
        return {"colleges": matched_colleges}, 200
        
    except Exception as e:
        return {"error": str(e)}

@app.route("/get-colleges/<state>/<college_email>")
def get_data(state, college_email):
    college_data, status_code = read(state, college_email)
    return jsonify(college_data), status_code

if __name__ == "__main__":
    app.run(debug=True)
