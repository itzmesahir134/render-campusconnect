import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
import pandas as pd
import io
from supabase import create_client, Client
import smtplib
import random
import ssl
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

otp_storage = {}
# Email Configuration
SENDER_EMAIL = "sahir.projects134@gmail.com"
SENDER_PASSWORD = "ykju twfs tkhw mopa"  # Use App Password for security

# Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate('/etc/secrets/ServiceAccountKey.json'))

def generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_otp_email(receiver_email, otp):
    """Send OTP via email (plaintext)."""
    subject = "Your Secure OTP Code"
    body = f"Your OTP Code is: {otp}\n\nUse the provided public key to encrypt and verify it."

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def start_otp_timer(email):
    """Remove OTP from memory after 1 minute."""
    time.sleep(120)
    if email in otp_storage:
        del otp_storage[email]
        print(f"OTP for {email} expired and was deleted.")

@app.route("/send-otp/<email>", methods=["GET"])
def send_otp(email):
    """Generate and send OTP to user's email."""

    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp = generate_otp()
    otp_storage[email] = otp  # Store plaintext OTP
    print(f"OTP Storage (before timer): {otp_storage}")

    # Start a thread to remove OTP after 1 minute
    threading.Thread(target=start_otp_timer, args=(email,), daemon=True).start()

    if send_otp_email(email, otp):
        return jsonify({"message": "OTP sent successfully!"}), 200
    else:
        return jsonify({"error": "Failed to send OTP"}), 500

@app.route("/verify-otp/<email>", methods=["GET"])
def verify_otp(email):
    """Verify the OTP without encryption."""
    otp = request.args.get("otp")  # Get the OTP from URL query parameter

    if not email or not otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    stored_otp = otp_storage.get(email)
    print(f"OTP Storage (at verification): {otp_storage}")

    if not stored_otp:
        return jsonify({"error": "Invalid or expired OTP"}), 400

    # Compare the received OTP with the stored OTP
    if stored_otp == otp:
        del otp_storage[email]  # Remove OTP after successful verification
        return jsonify({"response": True}), 200
    else:
        return jsonify({"response": False}), 200
#ref google object that is the full path to a document or collection
#doc_id is the unique number used as the document name
#user_id is the unique number given to a user 
#pressing space when defining a document/collection name can lead to issues as it dosen't appear on the document but does if mentioned in the document i.e 'DepartmentName'
#


# ISSUE: if user logs into the college from another account the user ID dosen't change (idk if we want to change that or not or have a way to keep multiple or just not use it)
#need to update Faculty to have their USER REFERENCE when they log in
#figure out how to change the 'MainCollegeHead' to 'CollegeHead' in 30 days timer
authorities = ['Main College Head','College Head','College Admin','Department Head','Department Admin', 'Instructor', 'Class Coordinator', 'Class Head', 'Student']




# Get Firestore database reference
db = firestore.client()
def createFire(collection_path, data, documentName=False):
    
    # Add the document to Firestore
    if documentName:
        doc_ref = db.collection(collection_path).document(documentName)
    else:
        doc_ref = db.collection(collection_path).document()
    doc_ref.set(data, merge=True)
    return doc_ref

def find_student_document(student_id, collegeDoc_id):
    departments_ref = db.collection(f"Colleges/{collegeDoc_id}/Departments").stream()

    for department_doc in departments_ref:
        department_name = department_doc.id  # Department name from document ID
        
        # Get all classes inside the department
        classes_ref = db.collection(f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes").stream()
        
        for class_doc in classes_ref:
            class_name = class_doc.id  # Class name from document ID
            
            # Get the student document reference
            student_doc_ref = db.collection(f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students").document(student_id)
            student_doc = student_doc_ref.get()
            
            if student_doc.exists:
                return student_doc_ref  # Return document reference if found

    return None


def find_all_possible_strings(input_string):
    substrings = []  # Initialize the list

    for i in range(len(input_string)):
        for j in range(i + 1, len(input_string) + 1):
            substrings.append(input_string[i:j])

    return substrings

# http://127.0.0.1:5000/read-for-signin/bjqenSCzXVbupX1E3OYs/ZLByMI4dkUa0vBxakiKbxIMCwvD3/Classes?department_name=Information%20Technology
@app.route("/read-for-user/<collegeDoc_id>/<userDoc_id>/<wanted_info>")
def readForUser(collegeDoc_id, userDoc_id, wanted_info):
    if wanted_info == "Departments":
        docs = db.collection(f"Colleges/{collegeDoc_id}/Departments").stream()
        return [doc.to_dict().get('DepartmentName') for doc in docs]
    elif wanted_info == "Classes":
        department_name = request.args.get('department_name')
        docs = db.collection(f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes").stream()
        return [doc.to_dict().get('ClassName') for doc in docs]
    
    
@app.route("/faculty-not-in-department/<collegeDoc_id>/<department_name>")
def faculty_not_in_department(collegeDoc_id, department_name):
    docs = db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream()
    finalList = [doc.to_dict() for doc in docs if department_name not in doc.to_dict().get('DepartmentList') ]
    names = []
    ids = []
    for doc in finalList:
        names.append(doc.get("Name"))
        ids.append(doc.get("IdentityID"))
    return {"FacultyName":names,"FacultyID":ids}, 200

@app.route("/update-faculty-departmentlist/<type>/<collegeDoc_id>/<department_name>/<faculty_id>")
def update_faculty_departmentlist(type, collegeDoc_id, department_name, faculty_id):
    doc_ref = db.collection(f"Colleges/{collegeDoc_id}/Faculty").document(faculty_id)
    if type == "Add":
        doc_ref.update({
            "DepartmentList": firestore.ArrayUnion([department_name]),
            f"ClassList.{department_name.replace(' ', '_')}": firestore.ArrayUnion([""])
        })
        return {"Response": "Added"}, 200
    elif type == "Remove":
        doc_ref.update({
            "DepartmentList": firestore.ArrayRemove([department_name]),
            f"ClassList.{department_name.replace(' ', '_')}": firestore.DELETE_FIELD
        })
        return {"Response": "Removed"}, 200

@app.route("/faculty-not-in-class/<collegeDoc_id>/<department_name>/<class_name>")
def faculty_not_in_class(collegeDoc_id, department_name, class_name):
    docs = db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream()
    facultyWithDep = [doc.to_dict() for doc in docs if department_name in doc.to_dict().get('DepartmentList')]
    finalList = [doc for doc in facultyWithDep if class_name not in doc.get('ClassList').get(department_name.replace(' ', '_'))]
    names = []
    ids = []
    for doc in finalList:
        names.append(doc.get("Name"))
        ids.append(doc.get("IdentityID"))
    return {"FacultyName":names,"FacultyID":ids, "FacultyDoc":[doc for doc in facultyWithDep if class_name in doc.get('ClassList').get(department_name.replace(' ', '_'))]}, 200



@app.route("/update-faculty-classlist/<type>/<collegeDoc_id>/<department_name>/<class_name>/<faculty_id>")
def update_faculty_classlist(type, collegeDoc_id, department_name, class_name, faculty_id):
    doc_ref = db.collection(f"Colleges/{collegeDoc_id}/Faculty").document(faculty_id)
    if type == "Add":
        doc_ref.update({
            f"ClassList.{department_name.replace(' ', '_')}": firestore.ArrayUnion([class_name])
        })
        return {"Response": "Added"}, 200
    elif type == "Remove":
        doc_ref.update({
            f"ClassList.{department_name.replace(' ', '_')}": firestore.ArrayRemove([class_name])
        })
        return {"Response": "Removed"}, 200
        
# @app.route("/college-login/<collegeDoc_id>/<userDoc_id>/<student_or_faculty>/<identity_id>")
# def collegeLogin(collegeDoc_id, userDoc_id, student_or_faculty, identity_id):
@app.route("/signin-college/<college_name>/<identity_id>/<college_email>/<password>/<userDoc_id>/<user_type>")
def collegeLogin(college_name, identity_id, college_email, password, userDoc_id, user_type):
    college_query = (
        db.collection("Colleges")
        .where("CollegeName", "==", college_name)
        .stream()
    )
    collegeDoc_id = None
    for doc in college_query:
        collegeDoc_id = doc.id  # Get document ID
        break
    if user_type == "Student": user_type = "Students"
    college_user_ref = db.collection(f"Colleges/{collegeDoc_id}/{user_type}").document(identity_id)  # Reference to document
    college_user_ref = college_user_ref.get()  # Get document
    if college_user_ref.exists:
        user_data = college_user_ref.to_dict()
        createFire(f'Users/{userDoc_id}/UserColleges',{
                    "UserType": user_data.get('UserType'),
                    "Authority": user_data.get('Authority'),
                    "CollegeEmail": college_email,
                    "CollegeName": college_name,
                    "isTeacher": False,
                    "Passsword": password,
                    "CollegeID": collegeDoc_id,
                    "IdentityID": identity_id,
                    "Roles":  user_data.get('Roles'),
                    "Keywords": find_all_possible_strings(college_name),
                    "DepartmentList": user_data.get("DepartmentList"),
                    "ClassList": user_data.get("ClassList")
                    
                    }, collegeDoc_id)
        if user_data.get('LoggedIn'):
            if user_data.get('Password') == password and user_data.get('CollegeEmail') == college_email:
                
                return jsonify({"response": True,"collegeInfo": collegeDoc_id}), 200
        else:
            if user_data.get('DefaultPassword') == password and user_data.get('CollegeEmail') == college_email:
                Name = db.collection(f"Users").document(userDoc_id).get().to_dict().get('full_name')
                createFire(f"Colleges/{collegeDoc_id}/{user_type}",{
                    "UserID": userDoc_id,
                    "UserDocID": userDoc_id,
                    "Password": password,
                    "LoggedIn": True,
                    "Name": Name
                    },identity_id)
                
                if user_type == "Student":
                    student_ref = find_student_document(identity_id, collegeDoc_id)
                    student_ref.set({
                        "UserID": userDoc_id,
                        "UserDocID": userDoc_id,
                        "Password": password,
                        "LoggedIn": True
                        }, merge=True)
                    
                return jsonify({"response": False,"collegeInfo": collegeDoc_id}), 200
        
    else:
        return jsonify({"response": False, "message": "Student not found"}), 404
    
@app.route("/change-college-pass/<collegeDoc_id>/<identity_id>/<default_pass>/<new_pass>/<college_email>/<user_type>")
def changePass(collegeDoc_id, identity_id, default_pass, new_pass, college_email, user_type):
    if user_type == "Student":
        ref = find_student_document(identity_id, collegeDoc_id)
    elif user_type == "Faculty":
        ref = db.collection(f"Colleges/{collegeDoc_id}/Faculty").document(identity_id)
        
    doc = ref.get().to_dict()
    if doc.get('Password') == default_pass or doc.get('DefaultPassword') == default_pass and doc.get('CollegeEmail') == college_email:
        ref.set({
            "Password": new_pass,
            "LoggedIn": True
            }, merge=True)
        if user_type == "Student":
            db.collection(f"Colleges/{collegeDoc_id}/Students").document(identity_id).set({
                "LoggedIn": True,
                "Password": new_pass
                }, merge = True)

# http://127.0.0.1:5000/college-login-search/Maharashtra/colleges
@app.route("/college-login-search/<state>/<college_name>")
def collegeLoginSearch(state, college_name):
    query = (
        db.collection("Colleges")
        .where("State", "==", state)
        .where("Keywords", "array_contains", college_name.lower())  # Search in keyword list
        .stream()
    )

    # Convert query to list
    college_list = [doc.to_dict().get("CollegeName", "") for doc in query]

    # Check if there are any results
    if not college_list:
        return jsonify(["None"]), 200  # No results found

    return jsonify(college_list), 200 

    
#http://127.0.0.1:5000/read-college-collection/Departments,Computer%20Science,Classes/bjqenSCzXVbupX1E3OYs/ZLByMI4dkUa0vBxakiKbxIMCwvD3
def remove_items_by_roles(removalList, listRemover):
    # Create a new list that excludes the unwanted roles
    outputList = [
        auth for auth in removalList if auth.get("Authority") in listRemover
    ]
    return outputList

def filter_by_authority(inputList, authority):
    # Check if the authority exists in the list
    if authority in inputList:
        # Get the index of the authority and return the sublist starting from it
        index = inputList.index(authority)
        return inputList[index+1:]

#['Main College Head','College Head','College Admin','Department Head','Department Admin', 'Instructor', 'Class Coordinator', 'Class Head', 'Student']
@app.route("/read-college-collection/<collection_name>/<collegeDoc_id>/<userDoc_id>")
def readCollegeCollections(collection_name, collegeDoc_id, userDoc_id):
    userAuthority = db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority')
    actionList = ['Main College Head','College Head','College Admin','Department Head','Department Admin']
    if  userAuthority in actionList:
        if ',' in collection_name:
            path = collection_name.split(',')
            way = '/'.join(path)
            docs = db.collection(f"Colleges/{collegeDoc_id}/{way}").stream()
            
            return [doc.to_dict() for doc in docs]
        else:
            docs = db.collection(f"Colleges/{collegeDoc_id}/{collection_name}").stream()
            filterList = filter_by_authority(authorities, userAuthority)
            if collection_name == "Faculty":
                return remove_items_by_roles([doc.to_dict() for doc in docs], filterList)
            elif collection_name == "Roles":
                return [doc.to_dict() for doc in docs if doc.to_dict().get("Authority") in filterList]
            return [doc.to_dict() for doc in docs]
    else: 
        return jsonify({"response": "No Authorization"})
    
@app.route("/find-faculty-authority/<authority>/<collegeDoc_id>")
def find_faculty_Authority(authority, collegeDoc_id):
    faculty = []
    facultyID = [] 
    docs = db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream()
    for doc in [doc.to_dict() for doc in docs]:
        for role in doc.get('Roles'):
            if db.collection(f"Colleges/{collegeDoc_id}/Roles").document(role).get().to_dict().get('Authority') == authority:
                faculty.append(doc.get('Name'))
                facultyID.append(doc.get('IdentityID'))
    
    if faculty != []:
        return {"response": True, "data": faculty, "ids": facultyID}
    else:
        return {"response": False, "data": f"Assign {authority} Authority"}

    
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

# http://127.0.0.1:5000/Colleges/bjqenSCzXVbupX1E3OYs/Setup/True
@app.route("/edit-field/<collection_path>/<document_name>/<field>/<value>")
def editField(collection_path, document_name, field, value):
    #Didn't add Authentication
    if ',' in collection_path:
            path = collection_path._split(',')
            collection_path = '/'.join(path)
    doc_ref = db.collection(collection_path).document(document_name)
    if value == "True": value = True
    elif value == "False": value = False
    doc_ref.set({
            field: value
        },merge = True)
    
    return jsonify({"response": True}), 200
    
    
    
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
@app.route("/create-colleges/<college_email>/<password>/<identity_id>/<college_name>/<state>/<userDoc_id>/<isHead>")
def create_college(college_email, password, identity_id, college_name, state, userDoc_id, isHead):
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
        # They are not the college head (Faculty Memeber)
        collegeHead_email = request.args.get('collegeHead_email')
    else:
        collegeHead_email = college_email
        
        
    data = readFire('Users',userDoc_id)
    
    #Create College
    college_ref = createFire('Colleges', {
        "Setup": True,
        "MainCollegeHead": collegeHead_email,
        "CollegeDomain": college_email.split('@')[1],
        "CollegeName": college_name,
        "State": state,
        "Keywords": find_all_possible_strings(college_name.lower())
        })
    if isHead == "true":
        createFire(f'Colleges/{college_ref.id}/Faculty', {
            "UserType": "Faculty",
            "Authority": "Main College Head",
            "Roles": ["Main College Head"],
            "CollegeEmail": request.args.get('collegeHead_email'),
            "CollegeDomain": college_email.split('@')[1],
            "CollegeName": college_name,
            "isTeacher": False,
            "Password": request.args.get('Headpassword'),
            "CollegeID": college_ref.id,
            "DefaultPassword": request.args.get('Headpassword'),
            "IdentityID": request.args.get('id'),
            "Keywords": find_all_possible_strings(college_name.lower()),
            "Display": False,
            "LoggedIn": False,
            "DepartmentList": [""],
            "ClassList": {"DefaultDepartmentName":[""]}
            },request.args.get('id'))
    
    createFire('Colleges',{
        "ID": college_ref.id
    },college_ref.id)
    
    #Update User Record
    createFire(f'Users/{userDoc_id}/UserColleges', {
        "UserType": data.get("UserType"),
        "Name": data.get("full_name"),
        "Authority": "Main College Head",
        "Roles": ["Main College Head"],
        "UserDocID": userDoc_id,
        "UserID": data.get('uid'),
        "CollegeEmail": college_email,
        "CollegeDomain": college_email.split('@')[1],
        "CollegeName": college_name,
        "isTeacher": False,
        "Password": password,
        "CollegeID": college_ref.id,
        "DefaultPassword": password,
        "IdentityID": identity_id,
        "Keywords": find_all_possible_strings(college_name.lower()),
        "Display": False,
        "Password": password,
        "LoggedIn": True,
        "DepartmentList": [""],
        "ClassList": {"DefaultDepartmentName":[""]}
        }, college_ref.id)

    #Create MainCollegeHead Faculty
    createFire(f'Colleges/{college_ref.id}/Faculty', {
        "UserType": "Faculty",
        "Name": data.get("full_name"),
        "UserDocID": userDoc_id,
        "UserID": data.get('uid'),
        "DefaultPassword": password,
        "Password": password,
        "LoggedIn": True,
        "IdentityID": identity_id,
        "Roles": ["Main College Head"],
        "CollegeEmail": college_email,
        "Display": False,
        "Authority": "Main College Head",
        "Password": password,
        "DepartmentList": [""],
        "ClassList": {"DefaultDepartmentName":[""]}
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
    
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') in ['Main College Head','College Head','College Admin','Department Head','Department Admin']:
        createFire(f'Colleges/{collegeDoc_id}/Courses',{
            "CourseName":course_name,
            "CourseCode":course_code,
            "Abbreviation": abbreviation
            }, course_code)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Courses").stream()]}), 200
     
# http://127.0.0.1:5000/add-role/TmjzpVsNRjNVHwidGrl0/Head%20Of%20Department/DepartmentHead/false/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False     
@app.route("/add-role/<collegeDoc_id>/<role_name>/<authority_level>/<is_teacher>/<userDoc_id>/<delete_prev>")
def add_role(collegeDoc_id, role_name, authority_level, is_teacher, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin','Department Head','Department Admin']:
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
    
    return jsonify({"response": True, "data": readCollegeCollections("Roles", collegeDoc_id, userDoc_id)}), 200

# http://127.0.0.1:5000/add-faculty/dPpg783dvE2N11hZVzps/Sahir%20Shaikh/oewhfniube@gmail.com/576364567/Pass@123/poggers/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
# http://127.0.0.1:5000/add-faculty/dPpg783dvE2N11hZVzps/Vivek/helo1vivek@gmail.com/4654w5/Pass@123/Head%20Of%20Department,Instructor/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
@app.route("/add-faculty/<collegeDoc_id>/<full_name>/<college_email>/<identity_id>/<default_password>/<role_name>/<userDoc_id>/<delete_prev>")
def add_faculty(collegeDoc_id, full_name, college_email, identity_id, default_password, role_name, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','CollegeHead','CollegeAdmin','Department Head']:
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
    userAuthorities = [doc.to_dict().get('Authority') for doc in db.collection(f"Colleges/{collegeDoc_id}/Roles").stream() if doc.to_dict().get('RoleName') in role_name]
    print(userAuthorities)
    print(authorities)
    userAuthority = None
    for auth in authorities:
        if auth in userAuthorities:
            userAuthority = auth
            break
    createFire(f'Colleges/{collegeDoc_id}/Faculty',{
        "UserType": "Faculty",
        "LoggedIn": False,
        "Name": full_name,
        "UserDocID": "Not Logged In",
        "UserID": "Not Logged In",
        "IdentityID": identity_id,
        "Roles": role_name,
        "CollegeEmail": college_email,
        "DefaultPassword": default_password,
        "Authority": userAuthority,
        "DepartmentList": [""],
        "ClassList": {"DefaultDepartmentName":[""]}
        }, identity_id)
    
    return jsonify({"response": True, "data": readCollegeCollections("Faculty", collegeDoc_id, userDoc_id)}), 200

#List of Programs = ['Certificate Program', 'Diploma Program', 'Associate Degree', 'Bachelor’s Degree', 'Post-Baccalaureate/Graduate Certificate', 'Master’s Degree', 'Doctoral Programs (Ph.D. or Professional Doctorates)', 'Post-Doctoral Studies']
# http://127.0.0.1:5000/add-department/bjqenSCzXVbupX1E3OYs/Mechanical%20Engineering/ME/Diploma%20in%20Engineering/Bhadti%20Rathod/Diploma%20Program/Semester/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
@app.route("/add-department/<collegeDoc_id>/<department_name>/<abbreviation>/<field_of_study>/<department_head_id>/<study_level>/<format>/<userDoc_id>/<delete_prev>")
def add_department(collegeDoc_id, department_name, abbreviation, field_of_study, department_head_id, study_level, format, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin']:
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
    hod_ref = db.collection(f'Colleges/{collegeDoc_id}/Faculty').document(department_head_id)
    update_faculty_departmentlist("Add", collegeDoc_id, department_name, department_head_id)
    dep_docs = readCollegeCollections(f'Departments,{department_name},Classes',collegeDoc_id, userDoc_id)
    for dep in dep_docs:
        update_faculty_classlist("Add", collegeDoc_id, department_name, dep.get('ClassName'), department_head_id)
    createFire(f'Colleges/{collegeDoc_id}/Departments',{
        "DepartmentHeadID": department_head_id,
        "DepartmentName": department_name,
        "Abbreviation": abbreviation,
        "FieldOfStudy": field_of_study,
        "DepartmentHead": hod_ref.get().to_dict().get('Name'),
        "Format": format,
        "StudyLevel": study_level,
        
        }, department_name)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Departments").stream()]}), 200

# http://127.0.0.1:5000/add-class/bjqenSCzXVbupX1E3OYs/Mechanical%20Engineering/ME/Diploma%20in%20Engineering/Bhadti%20Rathod/Diploma%20Program/Semester/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
@app.route("/add-class/<collegeDoc_id>/<department_name>/<class_name>/<class_coordinator_id>/<courses>/<format>/<year_or_semester>/<userDoc_id>/<delete_prev>")
def add_class(collegeDoc_id, department_name, class_name, class_coordinator_id, courses, format, year_or_semester, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin', 'Department Head', 'Department Admin']:
        return jsonify({"response": None}), 404
    
    if delete_prev == "True":
        old_class_name = request.args.get('old_class_name')
        db.collection(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes').document(old_class_name).delete()
    else:
        query = (
        db.collection(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes')
            .where("ClassName", "==", class_name)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
        
    if ',' in courses: courses = courses.split(',')
    else: courses = [courses]
    cc_ref = db.collection(f'Colleges/{collegeDoc_id}/Faculty').document(class_coordinator_id)
    update_faculty_departmentlist("Add", collegeDoc_id, department_name, class_coordinator_id)
    update_faculty_classlist("Add", collegeDoc_id, department_name, class_name, class_coordinator_id)
    createFire(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes',{
        "DepartmentName": department_name,
        "ClassName": class_name,
        "ClassCoordinator": cc_ref.get().to_dict().get('Name'),
        "ClassCoordinatorID": class_coordinator_id,
        "Courses": courses,
        "Format": format,
        "Year/Semester": year_or_semester,
        
        }, class_name)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes").stream()]}), 200


# /add-student/bjqenSCzXVbupX1E3OYs/Information%20Technology/A/TEster/12345678/hah@gmail.com/Pass@123/Class%20Representative/01,01,2501/01,01,2501/436357897/sadasd@gmail.com/ZLByMI4dkUa0vBxakiKbxIMCwvD3/True?old_student_id=57480220035
@app.route("/add-student/<collegeDoc_id>/<department_name>/<class_name>/<student_name>/<student_id>/<college_email>/<default_password>/<student_roles>/<from_date>/<to_date>/<phone_no>/<parent_email>/<userDoc_id>/<delete_prev>")
def add_student(collegeDoc_id, department_name, class_name, student_name, student_id, college_email, default_password, student_roles, from_date, to_date, phone_no, parent_email, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin','Department Head', 'Department Admin','Class Coordinator']:
        return jsonify({"response": None}), 404
    
    if delete_prev == "True":
        old_student_id = request.args.get('old_student_id')
        db.collection(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students').document(old_student_id).delete()
    else:
        query = (
        db.collection(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students')
            .where("IdentityID", "==", student_id)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
    
    if ',' in student_roles: student_roles = student_roles.split(',')
    else: student_roles = [student_roles]
    if 'Class Representative' in student_roles: authority = 'Class Representative'
    elif 'Class Vice-Representative' in student_roles: authority = 'Class Vice-Representative'
    elif 'Class Ladies-Representative' in student_roles: authority = 'Class Ladies-Representative'
    else: authority = 'Student'
    student_data = {
        "UserType": "Student",
        "LoggedIn": False,
        "IdentityID": student_id,
        "DepartmentName": department_name,
        "ClassName": class_name,
        "Name": student_name,
        "CollegeEmail": college_email,
        "DefaultPassword": default_password,
        "Roles": student_roles,
        "FromDate": from_date,
        "ToDate": to_date,
        "PhoneNo": phone_no,
        "ParentEmail": parent_email,
        "Password": "Not Logged In",
        "UserDocID": "Not Logged In",
        "UserID": "Not Logged In",
        "Authority": authority,
        "DepartmentList": ["",department_name],
        "ClassList": {"DefaultDepartmentName":[""],department_name:[class_name]}
        }
    
    createFire(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students', student_data, student_id)
    createFire(f'Colleges/{collegeDoc_id}/Students',student_data, student_id)
    
    return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students").stream()]}), 200

@app.route("/get-classes/<collegeDoc_id>/<deprtment_name>/<identityID>/<user_type>")
def get_classes(collegeDoc_id, deprtment_name, identityID, user_type):
    if user_type == "Student": user_type = "Students"
    return db.collection(f"Colleges/{collegeDoc_id}/{user_type}").document(identityID).get().to_dict().get('ClassList').get(deprtment_name), 200
    
    

@app.route("/reset-default/<collegeDoc_id>/<default_password>/<identity_id>/<userDoc_id>")
def resetToDefaultPass(collegeDoc_id, default_password, identity_id, userDoc_id):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin','Department Head', 'Department Admin','Class Coordinator']:
            return jsonify({"response": None}), 404
        
    createFire(f'Colleges/{collegeDoc_id}/Faculty',{
        "LoggedIn": False,
        "DefaultPassword": default_password,
        "Password": default_password
        }, identity_id)
    return jsonify({"response": True}), 200

@app.route("/reset-default-student/<collegeDoc_id>/<department_name>/<class_name>/<default_password>/<identity_id>/<userDoc_id>")
def resetToStudentDefaultPass(collegeDoc_id, department_name, class_name, default_password, identity_id, userDoc_id):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin']:
            return jsonify({"response": None}), 404
        
    createFire(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students',{
        "LoggedIn": False,
        "DefaultPassword": default_password,
        "Password": default_password
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
    

@app.route('/upload/excel/<collegeDoc_id>/<upload_function>/<userDoc_id>', methods=['POST'])
def upload_excel(collegeDoc_id, upload_function, userDoc_id):
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
    if ',' in upload_function: upload_function = upload_function.split(',')
    else: upload_function = [upload_function]
    
    if upload_function[0] == "AddFaculty":
        for facultyDoc in data:
            testRoles  = True
            
            roles = facultyDoc.get('Roles (No space after commas)')
            if "," in roles: roles = roles.split(",")
            else: roles = [roles]
            for i, v in enumerate(roles): roles[i] = v.strip()
            
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
    
    elif upload_function[0] == "AddStudents":
        for studentDoc in data:
            testRoles  = True
            print('ADD STUDENT FUNCTION')
            
            roles = studentDoc.get('Roles')
            if "," in roles: roles = roles.split(",")
            else: roles = [roles]
            for i, v in enumerate(roles): roles[i] = v.strip()
            for role in roles:
                if role in ['Student', 'Class Representative', 'Class Vice-Representative', 'Class Ladies-Representative']:
                    print(role)
                    continue
                else:
                    count -= 1
                    testRoles = False
                    break
                                                    # collegeDoc_id, department_name, class_name, student_name, student_id, college_email, default_password, student_roles, from_date, to_date, phone_no, parent_email, userDoc_id, delete_prev
            if testRoles: add_student(collegeDoc_id, upload_function[1], upload_function[2], str(studentDoc.get('Student Name')), str(studentDoc.get('Student ID')), str(studentDoc.get('College Email')), str(studentDoc.get('Default Password')), str(studentDoc.get('Roles')), str(studentDoc.get('From Date')), str(studentDoc.get('To Date')), str(studentDoc.get('Phone No')), str(studentDoc.get('Parent Email')), userDoc_id, False)
            count += 1
            print(count)
        return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Departments/{upload_function[1]}/Classes/{upload_function[2]}/Students").stream()], "added": str(count)})

    return jsonify({"response": "Add Proper Function Name"})

SUPABASE_URL = "https://ydpuhzopboechregfhti.supabase.co"  # Replace with your Supabase URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlkcHVoem9wYm9lY2hyZWdmaHRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzc5MDU1NjMsImV4cCI6MjA1MzQ4MTU2M30.aPJzxA8l2SoX3mYGWhIc49pstdYjbLXMtBDHVfcJFwU"  # Replace with your Supabase API Key

# Upload endpoint
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/upload/images', methods=['POST'])
def upload_to_supabase():
    BUCKET_NAME = "images"
    folder_path = request.form.get('folder_path')
    files = request.files.getlist('files')

    if not folder_path or not files:
        return jsonify({"error": "Missing folder path or files"}), 400

    uploaded_urls = []

    for file in files:
        try:
            # Read file content as bytes
            file_bytes = file.read()

            # Upload the file to Supabase storage
            file_path = f"{folder_path}/{file.filename}"
            res = supabase.storage.from_(BUCKET_NAME).upload(
                file_path, file_bytes, {'content-type': file.content_type}
            )

            # Get public URL
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
            uploaded_urls.append(public_url)

        except Exception as e:
            return jsonify({"error": f"Failed to upload {file.filename}", "details": str(e)}), 500

    return jsonify({"uploaded_urls": uploaded_urls}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    

@app.route("/")
def home():
    return "Welcome to College Finder API!"

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 5000))  # Use dynamic port for cloud hosting
    app.run(debug=True, host="0.0.0.0", port=PORT)

#pip install flask pandas openpyxl
