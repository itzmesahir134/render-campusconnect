import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
import pandas as pd
import io

#ref google object that is the full path to a document or collection
#doc_id is the unique number used as the document name
#user_id is the unique number given to a user 

#need to update Faculty to have their USER REFERENCE when they log in
#figure out how to change the 'MainCollegeHead' to 'CollegeHead' in 30 days timer
app = Flask(__name__)


# Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate('/etc/secrets/ServiceAccountKey.json'))

# Get Firestore database reference
db = firestore.client()
def createFire(collection_path, data, documentName=False):
    
    # Add the document to Firestore
    if documentName:
        doc_ref = db.collection(collection_path).document(documentName)
    else:
        doc_ref = db.collection(collection_path).document()
    doc_ref.set(data,merge=True)
    return doc_ref

@app.route("/read-college-collection/<collection_name>/<collegeDoc_id>/<userDoc_id>")
def readCollegeCollections(collection_name, collegeDoc_id, userDoc_id):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') in ['Main College Head','CollegeHead','CollegeAdmin','DepartmentHead','DepartmentAdmin']:
        docs = db.collection(f"Colleges/{collegeDoc_id}/{collection_name}").stream()
        return [doc.to_dict() for doc in docs]
    else: 
        return jsonify({"response": "No Authorization"})
    
@app.route("/find-faculty-Authority/<authority>/<collegeDoc_id>")
def find_faculty_Authority(authority, collegeDoc_id):
    faculty = []
    docs = db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream()
    for doc in [doc.to_dict() for doc in docs]:
        print('Faculty: ', doc.get('Name'))
        for role in doc.get('Roles'):
            print(role)
            if db.collection(f"Colleges/{collegeDoc_id}/Roles").document(role).get().to_dict().get('Authority') == authority:
                faculty.append(doc.get('Name'))
    
    if faculty != []:
        return faculty
    else:
        return {"Response": "Assign {authority} Authority"}

    
# @app.route("/read-doc/<collection_path>/<document_name>")
def readFire(collection_path, document_name):
    doc_ref = db.collection(collection_path).document(document_name)
    doc = doc_ref.get()
    return doc.to_dict()

@app.route("/read-field/<collection_path>/<document_name>/<field>")
def readField(collection_path, document_name, field):
    #Didn't add Authentication
    doc_ref = db.collection(collection_path).document(document_name)
    doc = doc_ref.get()
    return jsonify({"response": doc.to_dict().get(field)})

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
#http://127.0.0.1:5000/create-colleges/sahir@sbmp.ac.in/Anayah@123/23456789/No%20colleges%20found/ZLByMI4dkUa0vBxakiKbxIMCwvD3/false?collegeHead_email=&Headpassword=
@app.route("/create-colleges/<college_email>/<password>/<identity_id>/<college_name>/<userDoc_id>/<isHead>")
def create_college(college_email, password, identity_id, college_name, userDoc_id, isHead):
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
        
    data = readFire('Users',userDoc_id)
    
    #Create College
    college_ref = createFire('Colleges', {
        "Setup": True,
        "MainCollegeHead": collegeHead_email,
        "CollegeDomain": college_email.split('@')[1],
        "CollegeName": college_name
        
        })
    
    #Update User Record
    createFire(f'Users/{userDoc_id}/UserColleges', {
        "Authority": "Main College Head",
        "CollegeEmail": college_email,
        "CollegeDomain": college_email.split('@')[1],
        "CollegeName": college_name,
        "isTeacher": False,
        "CollegePassword": collegeHead_password,
        "CollegeID": college_ref.id,
        "IdentityID": identity_id,
        "Roles": ["Main College Head"]
        }, college_ref.id)
    
    #Create MainCollegeHead Faculty
    createFire(f'Colleges/{college_ref.id}/Faculty', {
        "Name": data.get("display_name"),
        "UserDocID": userDoc_id,
        "UserID": data.get('uid'),
        "IdentityID": identity_id,
        "Roles": ["Main College Head"],
        "CollegeEmail": college_email
        },identity_id)
    
    createFire(f'Colleges/{college_ref.id}/Roles', {
        "Authority": "Main College Head",
        "RoleName": "Main College Head",
        "isTeacher": False
    },"Main College Head")
    #u can access the name by doing doc_ref.id
        
    return jsonify({"response": True, "collegeInfo": college_ref.id}), 200

#http://127.0.0.1:5000/add-course/rZXfLAiNLehOuMMXoHet/Advanced%20Networl%20Administration/ANA2890025/ANA/ZLByMI4dkUa0vBxakiKbxIMCwvD3
# http://127.0.0.1:5000/add-course/TmjzpVsNRjNVHwidGrl0/Advanced%20Python/APY893951/APY/ZLByMI4dkUa0vBxakiKbxIMCwvD3/True?old_code=PYT893951
@app.route("/add-course/<collegeDoc_id>/<course_name>/<course_code>/<abbreviation>/<userDoc_id>/<delete_prev>")
def add_course(collegeDoc_id, course_name, course_code, abbreviation, userDoc_id, delete_prev):
    
    if delete_prev == "True":
        old_code = request.args.get('old_code')
        db.collection(f'Colleges/{collegeDoc_id}/Courses').document(old_code).delete()
    else:
        query = (
        db.collection(f'Colleges/{collegeDoc_id}/Courses')
            .where("CourseCode", "==", course_code)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
    
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') in ['Main College Head','CollegeHead','CollegeAdmin','DepartmentHead','DepartmentAdmin']:
        createFire(f'Colleges/{collegeDoc_id}/Courses',{
            "CourseName":course_name,
            "CourseCode":course_code,
            "Abbreviation": abbreviation
            }, course_code)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Courses").stream()]}), 200
     
# http://127.0.0.1:5000/add-role/TmjzpVsNRjNVHwidGrl0/Head%20Of%20Department/DepartmentHead/false/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False     
@app.route("/add-role/<collegeDoc_id>/<role_name>/<authority_level>/<is_teacher>/<userDoc_id>/<delete_prev>")
def add_role(collegeDoc_id, role_name, authority_level, is_teacher, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','CollegeHead','CollegeAdmin','DepartmentHead','DepartmentAdmin']:
        return jsonify({"response": None}), 404
    
    if delete_prev == "True":
        old_role = request.args.get('old_role')
        db.collection(f'Colleges/{collegeDoc_id}/Roles').document(old_role).delete()
    else:
        query = (
        db.collection(f'Colleges/{collegeDoc_id}/Roles')
            .where("RoleName", "==", role_name)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
        
    if is_teacher == "true": is_teacher = True
    else: is_teacher = False
    
    createFire(f'Colleges/{collegeDoc_id}/Roles',{
        "RoleName":role_name,
        "Authority":authority_level,
        "isTeacher": is_teacher
        }, role_name)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Roles").stream()]}), 200

# http://127.0.0.1:5000/add-faculty/dPpg783dvE2N11hZVzps/Sahir%20Shaikh/oewhfniube@gmail.com/576364567/Pass@123/poggers/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
# http://127.0.0.1:5000/add-faculty/dPpg783dvE2N11hZVzps/Vivek/helo1vivek@gmail.com/4654w5/Pass@123/Head%20Of%20Department,Instructor/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
@app.route("/add-faculty/<collegeDoc_id>/<full_name>/<college_email>/<identity_id>/<default_password>/<role_name>/<userDoc_id>/<delete_prev>")
def add_faculty(collegeDoc_id, full_name, college_email, identity_id, default_password, role_name, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','CollegeHead','CollegeAdmin']:
        return jsonify({"response": None}), 404
    
    if delete_prev == "True":
        old_id = request.args.get('old_id')
        db.collection(f'Colleges/{collegeDoc_id}/Faculty').document(old_id).delete()
    else:
        query = (
        db.collection(f'Colleges/{collegeDoc_id}/Faculty')
            .where("IdentityID", "==", identity_id)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
    
    if "," in role_name: role_name = role_name.split(",")
    else: role_name = [role_name]
    createFire(f'Colleges/{collegeDoc_id}/Faculty',{
        "LoggedIn": False,
        "Name": full_name,
        "UserDocID": "Not Logged In",
        "UserID": "Not Logged In",
        "IdentityID": identity_id,
        "Roles": role_name,
        "CollegeEmail": college_email,
        "DefaultPassword": default_password
        }, identity_id)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream()]}), 200

#List of Programs = ['Certificate Program', 'Diploma Program', 'Associate Degree', 'Bachelor’s Degree', 'Post-Baccalaureate/Graduate Certificate', 'Master’s Degree', 'Doctoral Programs (Ph.D. or Professional Doctorates)', 'Post-Doctoral Studies']
# http://127.0.0.1:5000/add-department/bjqenSCzXVbupX1E3OYs/Mechanical%20Engineering/ME/Diploma%20in%20Engineering/Bhadti%20Rathod/Diploma%20Program/Semester/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
@app.route("/add-department/<collegeDoc_id>/<department_name>/<abbreviation>/<field_of_study>/<department_head>/<study_level>/<format>/<userDoc_id>/<delete_prev>")
def add_department(collegeDoc_id, department_name, abbreviation, field_of_study, department_head, study_level, format, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','CollegeHead','CollegeAdmin']:
        return jsonify({"response": None}), 404
    
    if delete_prev == "True":
        old_department_name = request.args.get('old_department_name')
        db.collection(f'Colleges/{collegeDoc_id}/Departments').document(old_department_name).delete()
    else:
        query = (
        db.collection(f'Colleges/{collegeDoc_id}/Departments')
            .where("DepartmentName", "==", department_name)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
    
    createFire(f'Colleges/{collegeDoc_id}/Departments',{
        "DepartmentName": department_name,
        "Abbreviation": abbreviation,
        "FieldOfStudy": field_of_study,
        "DepartmentHead": department_head,
        "Format": format,
        "StudyLevel": study_level,
        
        }, department_name)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Departments").stream()]}), 200

@app.route("/reset-default/<collegeDoc_id>/<default_password>/<identity_id>/<userDoc_id>")
def resetToDefaultPass(collegeDoc_id, default_password, identity_id, userDoc_id):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin']:
            return jsonify({"response": None}), 404
        
    createFire(f'Colleges/{collegeDoc_id}/Faculty',{
        "LoggedIn": False,
        "DefaultPassword": default_password
        }, identity_id)
    return jsonify({"response": True}), 200


@app.route("/upload/CSV", methods=['POST'])
def upload_csv():
    # Check if the file is in the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # Ensure a file is selected
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Read the CSV file into a Pandas DataFrame
        df = pd.read_csv(io.StringIO(file.stream.read().decode("utf-8")))

        # Convert DataFrame to JSON
        data = df.to_dict(orient="records")
        
        return jsonify({"success": True, "data": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/upload/excel/<collegeDoc_id>/<userDoc_id>', methods=['POST'])
def upload_excel(collegeDoc_id, userDoc_id):
    # Check if file exists in the request
    if 'file' not in request.files:
        return jsonify({'response': 'No file part'}), 400
    
    file = request.files['file']
    
    # Ensure the file is selected
    if file.filename == '':
        return jsonify({'response': 'No selected file'}), 400

    # Read Excel file into a Pandas DataFrame
    df = pd.read_excel(io.BytesIO(file.read()), engine="openpyxl")

    # Convert DataFrame to JSON
    data = df.to_dict(orient="records")
    count = 0
    for facultyDoc in data:
        testRoles  = True
        
        roles = facultyDoc.get('Roles (No space after commas)')
        if "," in roles: roles = roles.split(",")
        else: roles = [roles]
        for role in roles:
            doc = db.collection(f"Colleges/{collegeDoc_id}/Roles").document(role).get()
            if doc.exists:
                continue
            else: 
                count -= 1
                testRoles = False
                break
        if testRoles: add_faculty(collegeDoc_id, str(facultyDoc.get('Full Name')), str(facultyDoc.get('College Email')), str(facultyDoc.get('Identity ID')), str(facultyDoc.get('Default Password')), str(facultyDoc.get('Roles (No space after commas)')), str(userDoc_id), False)
        count += 1
    

    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream()], "added": str(count)})



    

@app.route("/")
def home():
    return "Welcome to College Finder API!"

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 5000))  # Use dynamic port for cloud hosting
    app.run(debug=True, host="0.0.0.0", port=PORT)

#pip install flask pandas openpyxl
