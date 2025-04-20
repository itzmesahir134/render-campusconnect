import datetime
import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS  # Added CORS support
import pandas as pd
import io
from supabase import create_client, Client
import smtplib
import random
import ssl
import threading
import time
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

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

def serialize_firestore_data(data):
    if isinstance(data, dict):
        return {k: serialize_firestore_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_firestore_data(v) for v in data]
    elif hasattr(data, 'path'):  # likely a DocumentReference
        return str(data.path)
    else:
        return data

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
    user_ref = db.collection(f"Users/{doc_ref.get().to_dict().get('UserID')}/UserColleges").document(collegeDoc_id)
    if type == "Add":
        update = {
            "DepartmentList": firestore.ArrayUnion([department_name]),
            f"ClassList.{department_name.replace(' ', '_')}": firestore.ArrayUnion([""])
        }
        doc_ref.update(update)
        try:
            user_ref.update(update)
        except: print("User Ref not found")
        return {"Response": "Added"}, 200
    elif type == "Remove":
        update = {
            "DepartmentList": firestore.ArrayRemove([department_name]),
            f"ClassList.{department_name.replace(' ', '_')}": firestore.DELETE_FIELD
        }
        doc_ref.update(update)
        user_ref.update(update)
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
    user_ref = db.collection(f"Users/{doc_ref.get().to_dict().get('UserID')}/UserColleges").document(collegeDoc_id)
    
    if type == "Add":
        update = {
            f"ClassList.{department_name.replace(' ', '_')}": firestore.ArrayUnion([class_name])
        }
        doc_ref.update(update)
        user_ref.update(update)
        return {"Response": "Added"}, 200
    elif type == "Remove":
        update = {
            f"ClassList.{department_name.replace(' ', '_')}": firestore.ArrayRemove([class_name])
        }
        doc_ref.update(update)
        user_ref.update(update)
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
        collegeRef = doc.to_dict()
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
                    "ClassList": user_data.get("ClassList"),
                    "CollegeLogo": user_data.get("CollegeLogo")
                    
                    }, collegeDoc_id)
        
        if user_data.get('LoggedIn'):
            if user_data.get('Password') == password and user_data.get('CollegeEmail') == college_email:
                
                return jsonify({"response": True,"collegeInfo": collegeDoc_id}), 200
        else:
            if user_data.get('DefaultPassword') == password and user_data.get('CollegeEmail') == college_email:
                user_ref = db.collection(f"Users").document(userDoc_id)
                Name = user_ref.get().to_dict().get('full_name')
                photo_url = user_ref.get().to_dict().get('photo_url')
                createFire(f"Colleges/{collegeDoc_id}/{user_type}",{
                    "UserID": userDoc_id,
                    "UserDocRef": user_ref,
                    "Password": password,
                    "LoggedIn": True,
                    "Name": Name,
                    "photo_url": photo_url,
                    },identity_id)
                
                print(collegeRef.get('GlobalChat'))
                if collegeRef.get('GlobalChat'):
                    print('Adding to global chat')
                    ref = db.collection('Chats').document(collegeRef.get('GlobalChatID'))
                    ref.update({
                        "Members": firestore.ArrayUnion([Name]),
                        "MemberIDs": firestore.ArrayUnion([userDoc_id]),
                        "MemberProfiles": firestore.ArrayUnion([photo_url]),
                        "MemberUserRef": firestore.ArrayUnion([user_ref]),
                    })
                print(user_type)
                if user_type == "Students":
                    print('Updateing student')
                    student_ref = find_student_document(identity_id, collegeDoc_id)
                    student_ref.set({
                        "UserID": userDoc_id,
                        "UserDocID": user_ref,
                        "Password": password,
                        "LoggedIn": True,
                        "photo_url": user_ref.get().to_dict().get('photo_url'), 
                        }, merge=True)
                    
                return jsonify({"response": False,"collegeInfo": collegeDoc_id}), 200
        
    else:
        return jsonify({"response": False, "message": "Student not found"}), 404
    

#CHAT AREA
@app.route("/create-chat/<type>/<member_list>/<member_ids>")
def create_dm(type, member_list, member_ids):
    
    member_list = member_list.split(',')
    member_ids = member_ids.split(',')
    if request.args.get('DocID'):
        docID = request.args.get('DocID')
    else:
        docID = False
    query = (
    db.collection("Chats")
        .where("MemberIDs", "array_contains", member_ids[0])
        .stream()
    )
    refsList = [db.collection("Users").document(mem_id) for mem_id in member_ids]
    
    # Check if any documents exist
    if type == "Personal":
        if any(set(chat_doc.to_dict().get("MemberIDs",[])) == set(member_ids) for chat_doc in query ):
            return jsonify({"response": False}), 200
        
    chatDoc = createFire('Chats',{
        "type": type,
        "Members": member_list,
        "MemberProfiles": [ref.get().to_dict().get('photo_url') for ref in refsList],
        "MemberUserRef": refsList,
        "MemberIDs": member_ids,
        "last_message": "Say Hello!",
        "last_message_time": datetime.datetime.now(),
        "important": False,
    }, docID)
    if type == "Group":
        if request.args.get('collegeInfo'):  
            collegeInfo = request.args.get("collegeInfo")
        else: collegeInfo = "null"
        chatDoc.update({
            "GroupName": request.args.get('GroupName'),
            "GroupDescription": request.args.get('GroupDescription'),
            "GroupImage": request.args.get('GroupImage'),
            "ChatID": chatDoc.id,
            "collegeInfo": collegeInfo,
            })
    elif type == "Personal":
        chatDoc.update({
            "ChatID": chatDoc.id
        })
        
    return jsonify({"response": True, "chatID": chatDoc.id}), 200
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
            
            return [{**serialize_firestore_data(doc.to_dict())} for doc in docs]
        else:
            docs = db.collection(f"Colleges/{collegeDoc_id}/{collection_name}").stream()
            filterList = filter_by_authority(authorities, userAuthority)
            if collection_name == "Faculty":
                removeRef = [
                    {
                        **serialize_firestore_data(doc.to_dict())
                    }
                    for doc in docs
                ]
                return remove_items_by_roles(removeRef, filterList)
            elif collection_name == "Roles":
                return [doc.to_dict() for doc in docs if doc.to_dict().get("Authority") in filterList]
            
            return [{**serialize_firestore_data(doc.to_dict())} for doc in docs]
    else: 
        return jsonify({"response": "No Authorization"})

@app.route("/get-all-students/<collegeDoc_id>")
def get_all_students(collegeDoc_id):
    docs = [{**serialize_firestore_data(doc.to_dict())} for doc in db.collection(f"Colleges/{collegeDoc_id}/Students").stream() if doc.to_dict().get('LoggedIn')]
    if any(docs):
        return jsonify({"response": True, "documents": docs}), 200
    else:
        return jsonify({"response": False}), 200

@app.route("/get-all-faculty/<collegeDoc_id>")
def get_all_faculty(collegeDoc_id):
    return jsonify({"response": [{**serialize_firestore_data(doc.to_dict())} for doc in db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream() if doc.to_dict().get('LoggedIn')]}), 200
    
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
            "ClassList": {"DefaultDepartmentName":[""]},
            "Name": request.args.get("Name")
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
        #"UserDocID": userDoc_id,
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
        "UserDocID": db.collection('Users').document(userDoc_id),
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
    deps = doc = db.collection(f'Colleges/{collegeDoc_id}/Departments')
    if delete_prev == "True":
        old_department_name = request.args.get('old_department_name')
        deps.document(old_department_name)
        update_faculty_departmentlist("Remove",collegeDoc_id, department_name, doc.get().to_dict().get("DepartmentHeadID"))
        doc.delete()
    else:
        query = (
        deps
            .where("DepartmentName", "==", department_name)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
        
    fac_docs = db.collection(f'Colleges/{collegeDoc_id}/Faculty')
    for fac_doc in fac_docs.stream():
        fac_data = fac_doc.to_dict()
        if fac_data.get("Authority") in ['Main College Head', 'College Head', 'College Admin']:
            update_faculty_departmentlist(
                "Add",
                collegeDoc_id,
                department_name,
                fac_data.get("IdentityID", [])
            )
            
    hod_ref = fac_docs.document(department_head_id)
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

@app.route("/get-department-members/<collegeDoc_id>/<department_name>")
def get_department_members(collegeDoc_id, department_name):
    return [doc.to_dict().get('Name') for doc in db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream() if department_name in doc.to_dict().get('DepartmentList')] + [doc.to_dict().get('Name') for doc in db.collection(f"Colleges/{collegeDoc_id}/Students").stream() if department_name in doc.to_dict().get('DepartmentList')], 200

@app.route("/get-class-members/<collegeDoc_id>/<department_name>/<class_name>")
def get_class_members(collegeDoc_id, department_name, class_name):
    return [doc.to_dict().get('Name') for doc in db.collection(f"Colleges/{collegeDoc_id}/Faculty").stream() if department_name in doc.to_dict().get('DepartmentList') and class_name in doc.to_dict().get('ClassList').get(department_name.replace(' ','_'))] + [doc.to_dict().get('Name') for doc in db.collection(f"Colleges/{collegeDoc_id}/Students").stream() if department_name in doc.to_dict().get('DepartmentList') and class_name in doc.to_dict().get('ClassList').get(department_name.replace(' ','_'))], 200

# http://127.0.0.1:5000/add-class/bjqenSCzXVbupX1E3OYs/Mechanical%20Engineering/ME/Diploma%20in%20Engineering/Bhadti%20Rathod/Diploma%20Program/Semester/ZLByMI4dkUa0vBxakiKbxIMCwvD3/False
@app.route("/add-class/<collegeDoc_id>/<department_name>/<class_name>/<class_coordinator_id>/<courses>/<format>/<year_or_semester>/<userDoc_id>/<delete_prev>")
def add_class(collegeDoc_id, department_name, class_name, class_coordinator_id, courses, format, year_or_semester, userDoc_id, delete_prev):
    if db.collection(f'Users/{userDoc_id}/UserColleges').document(collegeDoc_id).get().to_dict().get('Authority') not in ['Main College Head','College Head','College Admin', 'Department Head', 'Department Admin']:
        return jsonify({"response": None}), 404
    
    classes_doc = db.collection(f'Colleges/{collegeDoc_id}/Departments/{department_name}/Classes')
    if delete_prev == "True":
        old_class_name = request.args.get('old_class_name')
        doc = classes_doc.document(old_class_name)
        update_faculty_classlist("Remove", collegeDoc_id, department_name, class_name, doc.get().to_dict().get("ClassCoordinatorID"))
        doc.delete()
    else:
        query = (
        classes_doc
            .where("ClassName", "==", class_name)
            .stream()
        )
    
        if any(query):  # Convert stream to list to evaluate results
            return jsonify({"response": False}), 200
        
    if ',' in courses: courses = courses.split(',')
    else: courses = [courses]
    
    fac_docs = db.collection(f'Colleges/{collegeDoc_id}/Faculty')
    for fac_doc in fac_docs.stream():
        if fac_doc.get().to_dict().get("Authority") in ['Main College Head','College Head','College Admin']:
            update_faculty_classlist("Add", collegeDoc_id, department_name, class_name, fac_doc.get().to_dict().get("IdentityID",[]))
            
    cc_ref = fac_docs.document(class_coordinator_id)
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
    
    # return jsonify({"response": True, "data": [doc.to_dict() for doc in db.collection(f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students").stream()]}), 200

    students = [
        {
            **serialize_firestore_data(doc.to_dict())
        }
        for doc in db.collection(
            f"Colleges/{collegeDoc_id}/Departments/{department_name}/Classes/{class_name}/Students"
        ).stream()
    ]

    return jsonify({"response": True, "data": students}), 200

@app.route("/get-classes/<collegeDoc_id>/<department_name>/<identityID>/<user_type>")
def get_classes(collegeDoc_id, department_name, identityID, user_type):
    if department_name == "": return [], 200
    if user_type == "Student": user_type = "Students"
    return db.collection(f"Colleges/{collegeDoc_id}/{user_type}").document(identityID).get().to_dict().get('ClassList').get(department_name.replace(' ','_')), 200


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

#UPLOAD ARE


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

    video_indexes = []
    uploaded_urls = []

    for index, file in enumerate(files):
        try:
            content_type = file.content_type
            if content_type.startswith('video/'):
                video_indexes.append(index)

            file_path = f"{folder_path}/{file.filename}"

            # Check if file exists by listing files in the folder
            existing_files = supabase.storage.from_(BUCKET_NAME).list(folder_path)
            file_exists = any(obj['name'] == file.filename for obj in existing_files)

            if file_exists:
                # File already exists, use existing public URL
                public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
                uploaded_urls.append(public_url)
                continue

            # Read file content as bytes
            file_bytes = file.read()

            # Upload the file
            supabase.storage.from_(BUCKET_NAME).upload(
                file_path, file_bytes, {'content-type': content_type}
            )

            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
            uploaded_urls.append(public_url)

        except Exception as e:
            return jsonify({
                "error": f"Failed to upload {file.filename}",
                "details": str(e)
            }), 500

    return jsonify({
        "uploaded_urls": uploaded_urls,
        "video_indexes": video_indexes
    }), 200





#ROLES
@app.route("/create-Roles/<p_ID>", methods=["GET"])
def create_Roles(p_ID):
    data = db.collection("Users").document(p_ID).get().to_dict()
    colleges = db.collection(f"Users/{p_ID}/UserColleges").stream()
    c=[]
    ids = []
    for college in colleges:
        createFire(f"Users/{p_ID}/Profile/p_text/collegeRoles",{
            "Roles":college.get("Roles"),
            "Name": college.get("CollegeName")
        }, college.id)
        c.append(college.get("CollegeName"))
        ids.append(college.id)
    
    createFire(f"Users/{p_ID}/Profile",{
        "collegeList": c,
        "collegeIdList": ids
        
    },"p_text")
    return {"colleges":c, "collegeIDs": ids},200
    

#Create Post
@app.route("/post/<p_ID>/<description>/<post>", methods=["GET"])
def create_posts(p_ID,description,post):
    data = db.collection("Users").document(p_ID).get().to_dict()

    # Get the post count dynamically
    post_collection_ref = db.collection(f"Users/{p_ID}/Post")
    count_query = post_collection_ref.count()
    count_snapshot = count_query.get()

    # Extract count properly
    # request_data = request.get_json() or {}
    post_number = count_snapshot[0][0].value -1 if count_snapshot else -1 
    # bio = request_data.get("bio", "Default Bio")
    # post_photo = request_data.get("post_photo", "unset")
    link = request.args.get('link')

    if not link:
            return jsonify({"error": "Missing link parameter"}), 400

        # Firestore update
    # Create post with a dynamic ID (incremented)
    post_id = post_number + 1
    post_ref = post_collection_ref.document(str(int(post_id)))  # Convert to string for Firestore ID

    post_ref.set({
        "uid":  post_id,
        post: link,
        "description": description,
    })

    return jsonify({"message": "Post successfully", "post_id": int(post_id)}),200


#Create Profile    
# @app.route("/create-default-profile/<p_ID>", methods=["GET"])
def create_default_profile(p_ID):
    #photo_type=False(supabase)  
    #photo_type=True(firebase)      
    data = db.collection("Users").document(p_ID).get().to_dict()
    

    colleges = data.get("colleges", [])  # Expected format: [{"college_name": "SBMP", "college_semORyr": "6-3"}, {...}]
    if not colleges:
        colleges = [{"college_name": "unset", "college_semORyr": "unset"}]
    pText = { 
        "display_name": data.get("display_name"),
        "p_email":data.get("email"),
        "uid": data.get("uid"),
        # "display_name":"name",
        # "p_email":"emaol",
        # "uid":"dsfv",
        "phone_No": "unset",
        "user_class":"unset",
        "bio": "unset",
        "college_name" : "unset",
        "college_semORyr": "unset",
        "GitHub":"unset",
        "Likedin":"unset",
        "YouTube":"unset",
        "Instagram":"unset",
    }
    pPhoto={
        # "profile_type":p_type,
        # "banner_type":b_type,
        # "profile_url":data.get("p_url"),
        # "banner_url":data.get("b_url")
        "profile_url":"unset",
        "banner_url":"unset",
        "photo_type":"",
        "banner_type":"",
        "file":""
        
    }
    postText={
        "description": "",
        "image":"",
    }

    createFire(f"Users/{p_ID}/Post",postText)
    createFire(f"Users/{p_ID}/Profile",pText,"p_text")
    createFire(f"Users/{p_ID}/Profile",pPhoto,"p_photo")
    
    return jsonify({"p_text":pText, "p_photo":pPhoto }),200

@app.route("/edit-profile-Name/<p_ID>/<bio>", methods=["GET"])
def edit_Name_bio(p_ID,bio):
    pText={
        "bio":bio
    }
    createFire(f"Users/{p_ID}/Profile",pText,"p_text")
    return jsonify({"p_text":pText, }),200


def create(doc_path, data):
    doc_ref = db.document(doc_path)  # 👈 Correct: doc path like "Users/<user_ID>"
    doc_ref.update(data)             # 👈 Updates fields like display_name, email etc.

@app.route("/edit-Name/<p_ID>/<display_name>", methods=["GET"])
def edit_Name(p_ID, display_name):
    # Update display_name in Users collection
    main_data = {
        "display_name": display_name
    }
    create(f"Users/{p_ID}", main_data)

    # Update display_name in Profile/p_text document
    profile_data = {
        "display_name": display_name
    }
    createFire(f"Users/{p_ID}/Profile", profile_data, "p_text")

    return jsonify({"message": "Display name updated", "p_text": profile_data}), 200



@app.route("/edit-ProfileImage/<p_ID>", methods=["GET"])
def edit_ProfileImage(p_ID):
    photo_url = request.args.get("link")
    if not photo_url:
        return jsonify({"error": "Missing 'link' parameter"}), 400

    p = {
        "photo_url": photo_url
    }
    create(f"Users/{p_ID}", p)
    profile_photo = {
        "photo_type": True,
        "profile_url": photo_url
    }
    createFire(f"Users/{p_ID}/Profile", profile_photo, "p_photo")
    return jsonify({"p_text": p}), 200


#Edit Profile  
@app.route("/edit-default-profile/<p_ID>/<display_name>/<uid>/<user_class>/<p_bio>/<college_name>/<college_semORyr>/<photo_url>/<posts>", methods=["GET"])
#@app.route("/edit-default-profile/<p_ID>/<display_name>/<email>/<uid>/<p_phone>/<user_class>/<p_bio>", methods=["GET"])

def edit_default_profile(p_ID,user_class,p_bio,college_name,college_semORyr,display_name,uid,photo_url,p_url,b_url,posts):
    #photo_type=False(supabase)  
    #photo_type=True(firebase)  
    photo_type=False

    pText= { 
        "display_name": display_name,
       # "p_email":email,
        "uid": uid,
        #"phone_No": p_phone,
        "user_class": user_class,
        "bio": p_bio,
        "college_name" : college_name,
        "college_semORyr": college_semORyr,
    }
    pPhoto={
        "photo_type":photo_type,
        "photo_url": photo_url,
        "profile_url":p_url,
        "banner_url":b_url
    }
    
    createFire(f"Users/{p_ID}/Profile",pText,"p_text")
    createFire(f"Users/{p_ID}/Profile",pPhoto,"p_photo")
    
    return jsonify({"p_text":pText, "p_photo":pPhoto }),200
@app.route('/upload/files', methods=['POST'])
def upload_filess():
    BUCKET_NAME = "images"
    FOLDER_NAME = request.form.get('FOLDER_NAME')
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = f"{FOLDER_NAME}/{file_name}"
    
    try:
        response = supabase.storage.from_(BUCKET_NAME).upload(file_path, file.read(), {'content-type': file.content_type})
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{file_path}"
        return jsonify({"message": "File uploaded successfully", "url": public_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
#EDIT Profile Image
@app.route("/edit-profile-image/<p_ID>/<path:photo_url>", methods=["GET","POST"])
def edit_profile_image(p_ID, photo_url):
    if "http" in photo_url:
        # Directly store in Firebase if it's already a URL
        pPhoto = {
            "photo_type": True,
            "profile_url": photo_url
        }
        createFire(f"Users/{p_ID}/Profile", pPhoto, "p_photo")
        return jsonify({"message": "Profile image updated from URL", "p_photo": pPhoto}), 200
    else:
        # Check if an image file is provided
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        image = request.files['image']
        filename = image.filename
        temp_path = os.path.join("temp_uploads", filename)

        try:
            # Create temp directory if not exists
            os.makedirs("temp_uploads", exist_ok=True)
            
            # Save the file temporarily
            image.save(temp_path)

            # Upload the saved file to Supabase
            with open(temp_path, "rb") as file:
                response = supabase.storage.from_("profile").upload(
                    file=file,
                    path=f"pro/{filename}",
                    file_options={"cache-control": "3600", "upsert": "false"}
                )

            # Delete the temp file after upload
            os.remove(temp_path)

            if not response:
                return jsonify({"error": "Upload to Supabase failed"}), 500

            # Get public URL
            public_url = supabase.storage.from_("profile").get_public_url(f"pro/{filename}")

            # Store in Firebase
            pPhoto = {
                "photo_type": False,
                "profile_url": public_url
            }
            createFire(f"Users/{p_ID}/Profile", pPhoto, "p_photo")

            return jsonify({"message": "Profile image uploaded & updated", "p_photo": pPhoto}), 200

        except Exception as e:
             return jsonify({"error": str(e)}), 500


@app.route("/edit-profile-banner/<p_ID>/<path:banner_url>", methods=["GET","POST"])
def edit_profile_banner(p_ID, banner_url):
    if "http" in banner_url:
        # Directly store in Firebase if it's already a URL
        pPhoto = {
            "photo_type": True,
            "banner_url": banner_url
        }
        createFire(f"Users/{p_ID}/Profile", pPhoto, "p_photo")
        return jsonify({"message": "Profile image updated from URL", "p_photo": pPhoto}), 200
    else:
        # Check if an image file is provided
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400

        image = request.files['image']
        filename = image.filename
        temp_path = os.path.join("temp_uploads", filename)

        try:
            # Create temp directory if not exists
            os.makedirs("temp_uploads", exist_ok=True)
            
            # Save the file temporarily
            image.save(temp_path)

            # Upload the saved file to Supabase
            with open(temp_path, "rb") as file:
                response = supabase.storage.from_("profile").upload(
                    file=file,
                    path=f"banner/{filename}",
                    file_options={"cache-control": "3600", "upsert": "false"}
                )

            # Delete the temp file after upload
            os.remove(temp_path)

            if not response:
                return jsonify({"error": "Upload to Supabase failed"}), 500

            # Get public URL
            public_url = supabase.storage.from_("profile").get_public_url(f"banner/{filename}")

            # Store in Firebase
            pPhoto = {
                "photo_type": False,
                "banner_url": public_url
            }
            createFire(f"Users/{p_ID}/Profile", pPhoto, "p_photo")

            return jsonify({"message": "Profile image uploaded & updated", "p_photo": pPhoto}), 200

        except Exception as e:
             return jsonify({"error": str(e)}), 500


@app.route("/edit-post/<p_ID>/<platform>", methods=["GET"])
def edit_post(p_ID,platform):
    try:
        link = request.args.get('link')

        if not link:
            return jsonify({"error": "Missing link parameter"}), 400

        # Firestore update
        pPhoto = {platform: link}
        success = createFire(f"Users/{p_ID}/Post", pPhoto, "jaze3ZCduzcBvfqfIXlw")

        if not success:
            return jsonify({"error": "Failed to update Firestore"}), 500

        return jsonify({
            "message": f"{platform} link updated successfully",
            "updated_link": link,
            "p_text": pPhoto
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update link: {str(e)}"}), 500
         
@app.route("/edit-pImage/<p_ID>/<platform>", methods=["GET"])
def edit_pImage(p_ID,platform):
    try:
        link = request.args.get('link')

        if not link:
            return jsonify({"error": "Missing link parameter"}), 400

        # Firestore update
        pPhoto = {platform: link}
        success = createFire(f"Users/{p_ID}/Profile", pPhoto, "p_photo")

        if not success:
            return jsonify({"error": "Failed to update Firestore"}), 500

        return jsonify({
            "message": f"{platform} link updated successfully",
            "updated_link": link,
            "p_text": pPhoto
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to update link: {str(e)}"}), 500

#CREATE LINKS
@app.route('/edit-link/<p_ID>/<platform>', methods=['GET'])
def update_link(p_ID, platform):
    try:
        link = request.args.get('link')

        if not link:
            return jsonify({"error": "Missing link parameter"}), 400

        # Firestore update
        pText = {platform: link}
        success = createFire(f"Users/{p_ID}/Profile", pText, "p_text")

        if not success:
            return jsonify({"error": "Failed to update Firestore"}), 500

        return jsonify({
            "message": f"{platform} link updated successfully",
            "updated_link": link,
            "p_text": pText
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to update link: {str(e)}"}), 500


# Fetch Profile

#http://127.0.0.1:5000/fetch-profile/VIc9yUl80yfQoSYcoesyWozVBVa2
@app.route("/fetch-profile/<p_ID>", methods=["GET"])

def fetch_profile(p_ID):
    #photo_type=False(supabase)  
    #photo_type=True(firebase)  

    docs = db.collection(f"Users/{p_ID}/Profile").limit(1).stream()
    
    if any (docs):
        
        p_text = db.collection(f"Users/{p_ID}/Profile").document("p_text").get().to_dict()
        p_photo = db.collection(f"Users/{p_ID}/Profile").document("p_photo").get().to_dict()

        #if "http"  in p_photo.get("photo_url"): photo_type = True

        return jsonify({"p_text":p_text, "p_photo":p_photo }),200
    else:
        return create_default_profile(p_ID),200

@app.route("/get-Roles/<p_ID>/<college_id>")
def get_Roles(p_ID,college_id):
    college_Roles= db.collection(f"Users/{p_ID}/Profile/p_text/collegeRoles").document(college_id).get().to_dict().get("Roles")
    return college_Roles,200

@app.route("/get-link/<p_ID>",methods=["GET"])
def fetch_link(p_ID):
    links_ref = db.collection(f"Users/{p_ID}/Profile/p_text/Links").stream()
    links = {}
    for doc in links_ref:
        links.update(doc.to_dict())  # Merge all documents
    return jsonify({"links": links}), 200

@app.route('/get-Post/<p_ID>', methods=['GET'])
def get_post(p_ID):
    try:
        # Access 'Posts' subcollection for user with ID = p_ID
        posts_ref = db.collection('Users').document(p_ID).collection('Posts')
        docs = posts_ref.stream()

        posts = []
        for doc in docs:
            data = doc.to_dict()
            data['post_id'] = doc.id  # Add the document ID
            posts.append(data)

        return jsonify({'posts': posts}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch posts: {str(e)}'}), 500


@app.route('/create-form/<user_id>', methods=['GET'])
def createForm(user_id):
    # user_id = request.args.get('user_id')
    if not user_id:
            return jsonify({"error": "user_id is required"}), 400
    form_id = str(uuid.uuid4())

    form_doc = {
        'title': "Untitled Form",
        'desc': "No description...",
        'fields': [],
        "user_id": user_id,
        'form_id': form_id
    }

    db.collection('Forms').document(form_id).set(form_doc)
    return jsonify({"success": True, "message": "Form created", "form_id": form_id}), 201

@app.route('/create-ass/<user_id>', methods=['GET'])
def createFAss(user_id):
    # user_id = request.args.get('user_id')
    if not user_id:
            return jsonify({"error": "user_id is required"}), 400
    ass_id = str(uuid.uuid4())

    ass_doc = {
        'title': "Untitled Form",
        'desc': "No description...",
        'fields': [],
        "user_id": user_id,
        'assignment_id': ass_id
    }

    db.collection('Assignment').document(assignment_id).set(ass_doc)
    return jsonify({"success": True, "message": "Ass created", "assignment_id": assignemnt_id}), 201


def returnAllFields(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return []

    form_data = form_doc.to_dict()
    return form_data.get("fields", [])  # Ensure "fields" key exists

def parse_formatted_string(input_str):
    groups = input_str.split("@@@@@")  # Split different form groups
    result = []

    for group in groups:
        fields = group.split(",,,,,")  # Split key-value pairs
        form_dict = {}

        for field in fields:
            if ":::::" in field:
                key, value = field.split(":::::", 1)
                value = value.strip()

                # Convert boolean values
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False

                # Convert list values (detects `,,,` as a separator)
                elif ",,," in value:
                    value = value.split(",,,")  # Convert to list

                form_dict[key] = value  # Store in dictionary

        result.append(form_dict)

    return result

def debugForm(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    form_data = form_doc.to_dict() or {}
    return jsonify(form_data), 200


@app.route('/update-form-metadata/<form_id>', methods=['GET'])
def update_form_metadata(form_id):
    if not form_id:
        return jsonify({"error": "Missing form_id"}), 400

    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()

    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404

    updated_data = {}
    if "form_title" in request.args:
        updated_data["title"] = request.args.get("form_title")
    if "form_desc" in request.args:
        updated_data["desc"] = request.args.get("form_desc")
    if "editable_responses" in request.args:
        updated_data["editable_responses"] = request.args.get("editable_responses").lower() == "true"

    if updated_data:
        form_ref.set(updated_data, merge=True)
    
    # Fetch updated document
    updated_doc = form_ref.get().to_dict()
    
    return jsonify({
            "message": "Form metadata updated successfully", 
            "title": updated_doc.get("title", "Untitled Form"), 
            "desc": updated_doc.get("desc", "No description"),
            "editable_responses": updated_doc.get("editable_responses", False)
        }), 200


@app.route('/update-form-fields/<form_id>/<field_id>/<field_type>', methods=['GET'])
def update_form_fields(form_id, field_id, field_type):
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    
    field_ref = fields_collection.document(field_id)
    field_doc = field_ref.get()
    
    if not field_doc.exists:
        return jsonify({"error": "Field not found"}), 404
    
    update_data = {}
    if "label" in request.args:
        update_data["label"] = request.args.get("label")
    if "required" in request.args:
        update_data["required"] = request.args.get("required").lower() == "true"
    if "file" in request.args:
        update_data["file"] = request.args.get("file")
    if "options" in request.args:
        new_option = request.args.get("options")
        existing_options = field_doc.to_dict().get("options", [])
        if new_option not in existing_options:
            existing_options.append(new_option)
        update_data["options"] = existing_options
    if "correct_option" in request.args:
        update_data["correct_option"] = request.args.get("correct_option")
    if "remove_option" in request.args:
        remove_option = request.args.get("remove_option")
        existing_options = field_doc.to_dict().get("options", [])
        if remove_option in existing_options:
            existing_options.remove(remove_option)
        update_data["options"] = existing_options

    
    if update_data:
        field_ref.set(update_data, merge=True)
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "Field updated successfully", "fields": updated_fields}), 200

@app.route('/add-form-field/<form_id>/<field_type>', methods=['GET'])
def add_form_field(form_id, field_type):
    if not field_type:
        return jsonify({"error": "Missing field_type"}), 400
    
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    new_field_id = str(uuid.uuid4())
    new_field = {
        "label": f"New {field_type}",
        "type": field_type,
        "options": [],
        "correct_option": "",
        "required": False,
        "field_id": new_field_id,
        "created_at": firestore.SERVER_TIMESTAMP,
        "form_id": form_id
    }
    fields_collection.document(new_field_id).set(new_field, merge=True)
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "New field added successfully", "field_id": new_field_id, "fields": updated_fields}), 200


@app.route('/create-response/<form_id>/<use_id>/<user_id>', methods=['GET'])
def create_or_get_response(form_id, use_id, user_id):
    if not form_id or not user_id:
        return jsonify({"error": "Missing form_id or user_id"}), 400

    responses_ref = db.collection("Responses")
    existing_response = responses_ref.where("form_id", "==", form_id).where("user_id", "==", user_id).limit(1).stream()

    for doc in existing_response:
        return jsonify({"response_id": doc.id, "exists": True})  # Response exists

    # If no response found, create one
    new_response_ref = responses_ref.document()
    response_id = new_response_ref.id  # Generate unique document ID
    new_response_ref.set({
        "response_id": response_id,
        "form_id": form_id,
        "user_id": user_id,
        "submitted_at": firestore.SERVER_TIMESTAMP,
        "use_id": use_id,
        "approval_status": "Pending",
        "fields": []
    })

    return jsonify({"response_id": response_id, "exists": False})  # New response created

# @app.route('/update-response/<response_id>/<field_id>', methods=['GET'])
# def update_response(response_id, field_id):
#     label = request.args.get('label')
#     answer = request.args.get('answer')
#     field_type = request.args.get('field_type')  # Get field type from request
#     approval_status = request.args.get('approval_status')

#     if not response_id or not field_id or not label or answer is None or not field_type:
#         return jsonify({"error": "Missing required parameters"}), 400

#     # Get form_id from parent document
#     form_id = response_doc.to_dict().get("form_id")
#     if not form_id:
#         return jsonify({"error": "form_id not found in response document"}), 400

#     isRequired = 
            
#     # Determine how to store the answer based on field type
#     update_data = {
#         "label": label,
#         "updated_at": firestore.SERVER_TIMESTAMP,
#         "field_id":field_id,
#         "form_id": form_id,
#         "required": 
#     }

#     if field_type == "checkbox":
#         update_data["answers"] = answer.split(",,") if ",," in answer else [answer]  # Store as list under 'answers'
#     else:
#         update_data["answer"] = answer  # Store as a string under 'answer' for other field types

#     try:
#         print(f"Updating Response: {response_id}, Field: {field_id}")
#         print(f"Label: {label}, Field Type: {field_type}, Data: {update_data}")

#         # Reference to Firestore
#         field_ref = db.collection('Responses').document(response_id).collection('responded_fields').document(field_id)

#         # Check if the document exists
#         doc = field_ref.get()
#         print(f"Document Exists: {doc.exists}")

#         # Update Firestore
#         field_ref.set(update_data, merge=True)

#         print("Firestore Update Successful!")

#         return jsonify({"message": "Response updated"}), 200

#     except Exception as e:
#         print(f"Firestore Error: {e}")
#         return jsonify({"error": str(e)}), 500


@app.route('/update-response/<response_id>/<field_id>', methods=['GET'])
def update_response(response_id, field_id):
    label = request.args.get('label')
    answer = request.args.get('answer')
    field_type = request.args.get('field_type')
    approval_status = request.args.get('approval_status')

    if not response_id or not field_id or not label or answer is None or not field_type:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        print(f"Updating Response: {response_id}, Field: {field_id}")

        #Get parent Responses document for form_id
        response_doc_ref = db.collection('Responses').document(response_id)
        response_doc = response_doc_ref.get()

        if not response_doc.exists:
            return jsonify({"error": "Response document not found"}), 404

        form_id = response_doc.to_dict().get("form_id")
        if not form_id:
            return jsonify({"error": "form_id not found in response document"}), 400

        # Get required field from Fields subcollection
        field_doc_ref = db.collection('Forms').document(form_id).collection('fields').document(field_id)
        field_doc = field_doc_ref.get()

        if not field_doc.exists:
            return jsonify({"error": "Field document not found in Forms collection"}), 404

        required = field_doc.to_dict().get("required", False)  # default to False if not set

        # Step 3: Build update data
        update_data = {
            "label": label,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "field_id": field_id,
            "form_id": form_id,
            "required": required
        }

        if field_type == "checkbox":
            update_data["answers"] = answer.split(",,") if ",," in answer else [answer]
        else:
            update_data["answer"] = answer

        # Step 4: Update responded_fields document
        field_ref = response_doc_ref.collection('responded_fields').document(field_id)
        field_ref.set(update_data, merge=True)

        print("Firestore Update Successful!")
        return jsonify({"message": "Response updated"}), 200

    except Exception as e:
        print(f"Firestore Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/delete-response/<response_id>', methods=['GET'])
def delete_response(response_id):
    try:
        response_ref = db.collection("Responses").document(response_id)
        if not response_ref.get().exists:
            return jsonify({"error": "Response not found"}), 404
        
        response_ref.delete()
        return jsonify({"message": "Response deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-form/<form_id>', methods=['GET'])
def delete_form(form_id):
    form_ref = db.collection("Forms").document(form_id)
    form_doc = form_ref.get()
    
    if not form_doc.exists:
        return jsonify({"error": "Form not found"}), 404
    
    form_ref.delete()
    return jsonify({"message": "Form deleted successfully"}), 200

@app.route('/delete-form-field/<form_id>/<field_id>', methods=['GET'])
def delete_form_field(form_id, field_id):
    form_ref = db.collection("Forms").document(form_id)
    fields_collection = form_ref.collection("fields")
    field_ref = fields_collection.document(field_id)
    field_doc = field_ref.get()
    
    if not field_doc.exists:
        return jsonify({"error": "Field not found"}), 404
    
    field_ref.delete()
    
    fields_snapshot = fields_collection.stream()
    updated_fields = [{"id": field.id, **field.to_dict()} for field in fields_snapshot]
    
    return jsonify({"message": "Field deleted successfully", "fields": updated_fields}), 200

@app.route('/create-activity/<user_id>', methods=['GET'])
def create_activity(user_id):
    try:
        # user_id = request.args.get("user_id")
        form_id = request.args.get("form_id", "")
        activity_title = request.args.get("activity_title", "New Activity")
        activity_desc = request.args.get("activity_desc", "Description here")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        status = request.args.get("status", "Open")

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        activity_id = str(uuid.uuid4())
        activity_data = {
            "activity_id": activity_id,
            "activity_title": activity_title,
            "activity_desc": activity_desc,
            "start_date": datetime.datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
            "end_date": datetime.datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
            "created_on": firestore.SERVER_TIMESTAMP,
            "status": status,
            "user_id": user_id,
            "form_id": form_id
        }

        db.collection("Activities").document(activity_id).set(activity_data)

        return jsonify({"message": "Activity created successfully", "activity_id": activity_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-activity/<activity_id>', methods=['GET'])
def delete_activity(activity_id):
    try:
        activity_ref = db.collection("Activities").document(activity_id)
        if not activity_ref.get().exists:
            return jsonify({"error": "Activity not found"}), 404
        
        activity_ref.delete()
        return jsonify({"message": "Activity deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update-activity/<user_id>/<activity_id>', methods=['GET'])
def update_activity(user_id, activity_id):
    try:
        data = request.args

        activity_ref = db.collection('Activities').document(activity_id)
        activity_doc = activity_ref.get()

        if not activity_doc.exists:
            return jsonify({"error": "Activity not found"}), 404

        activity_data = activity_doc.to_dict()
        if activity_data.get("user_id") != user_id:
            return jsonify({"error": "Unauthorized access"}), 403

        update_data = {}
        for key in ["activity_title", "activity_desc", "status", "form_id"]:
            if key in data:
                update_data[key] = data.get(key)

        for key in ["start_date", "end_date"]:
            if key in data:
                try:
                    update_data[key] = datetime.datetime.strptime(data.get(key), "%d/%m/%Y")
                except ValueError:
                    return jsonify({"error": f"Invalid date format for {key}, expected YYYY-MM-DD"}), 400

        if not update_data:
            return jsonify({"error": "No fields to update"}), 400

        update_data["updated_on"] = firestore.SERVER_TIMESTAMP
        activity_ref.set(update_data, merge=True)

        return jsonify({"message": "Activity updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#if __name__ == '__main__':
   # app.run(host='0.0.0.0', port=5000, debug=True)
    

@app.route("/")
def home():
    return "Welcome to College Finder API!"

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 5000))  # Use dynamic port for cloud hosting
    app.run(debug=True, host="0.0.0.0", port=PORT)

#pip install flask pandas openpyxl
