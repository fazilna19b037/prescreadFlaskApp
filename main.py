import os
from app import app
import urllib.request
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import azure
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import TextOperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import TextRecognitionMode
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from msrest.authentication import CognitiveServicesCredentials
import os
import sys
import requests
import time

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/', methods=['POST'])
def upload_image():
    
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        #print('upload_image filename: ' + filename)
        flash("Results can be found below:-")
        output=master("./static/uploads/"+filename)
        return render_template('upload.html', filename=filename,output=output)
    else:
        flash('Allowed image types are -> png, jpg, jpeg, gif')
        return redirect(request.url)

@app.route('/display/<filename>')
def display_image(filename):
    #print('display_image filename: ' + filename)
    return redirect(url_for('static', filename='uploads/' + filename), code=301)

def master(remote_image_url):
    os.environ['COMPUTER_VISION_SUBSCRIPTION_KEY']='ab3644d6a0fd4a64830e6c9830b135d8'
    os.environ['COMPUTER_VISION_ENDPOINT']='https://drcomputervision.cognitiveservices.azure.com/'
    
    
    if 'COMPUTER_VISION_SUBSCRIPTION_KEY' in os.environ:
        subscription_key = os.environ['COMPUTER_VISION_SUBSCRIPTION_KEY']
    else:
        print("\nSet the COMPUTER_VISION_SUBSCRIPTION_KEY environment variable.\n*Restart your shell or IDE for changes to take effect.*")
        sys.exit()
    
    if 'COMPUTER_VISION_ENDPOINT' in os.environ:
        endpoint = os.environ['COMPUTER_VISION_ENDPOINT']
    else:
        print("\nSet the COMPUTER_VISION_ENDPOINT environment variable.\n*Restart your shell or IDE for changes to take effect.*")
        sys.exit()
    
    computervision_client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))
    #print("===== Batch Read File - remote =====")
    
    with open(remote_image_url, 'rb') as image_url:
      remote_image_printed_text_url = image_url
      recognize_printed_results = computervision_client.batch_read_file_in_stream(remote_image_printed_text_url,  raw=True)
      operation_location_remote = recognize_printed_results.headers["Operation-Location"]
      operation_id = operation_location_remote.split("/")[-1]
    
    while True:
        get_printed_text_results = computervision_client.get_read_operation_result(operation_id)
        if get_printed_text_results.status not in ['NotStarted', 'Running']:
            break
        time.sleep(1)
    raw_text=""" """
    if get_printed_text_results.status == TextOperationStatusCodes.succeeded:
        for text_result in get_printed_text_results.recognition_results:
            for line in text_result.lines:
                raw_text+=line.text
                raw_text+=" "

  #print(raw_text)
  #print(list(raw_text.split(" ")))

    subscription_key = "37f1d616c15e4b188df6530a1b3a4721"
    endpoint = "https://healthanalytics37.cognitiveservices.azure.com/"
    
    def authenticate_client():
        ta_credential = AzureKeyCredential(subscription_key)
        text_analytics_client = TextAnalyticsClient(
                endpoint=endpoint, 
                credential=ta_credential)
        return text_analytics_client
    
    
    def entity_recognition_example(client):
        final_text=""
        output=[]
        try:
            documents = [raw_text]
            result = client.recognize_entities(documents = documents)[0]
    
            #print("-----------------------")
            for entity in result.entities:
                if entity.category=='Person':
                    j=True
                    names=list(entity.text.split(" "))
                    raw_list=list(raw_text.split(" "))
                    for x in names:
                        for y in raw_list:
                            if x==y:
                                i=raw_list.index(x)
                            if raw_list[i-1]=='Dr':
                                j=False
                        #print("Doctor Name is Dr.{}".format(entity.text))
                            output.append("\nDoctor Name is Dr.{} \n".format(entity.text))
                            final_text+="\nDoctor Name is Dr.{} \n".format(entity.text)
                    if j:
                  #print("Name is {}".format(entity.text))
                        output.append("\nName is {} \n".format(entity.text))
                        final_text+="\nName is {} \n".format(entity.text)
                if entity.category=='Address':
                  #print("Address is {}".format(entity.text))
                    output.append("\nAddress is {} \n".format(entity.text))
                    final_text+="\nAddress is {} \n".format(entity.text)
                    
    
        except Exception as err:
            print("Encountered exception. {}".format(err))
    
        return output
    
    
    def health_example(client):
        final_text=""
        output=[]
        documents = [
            raw_text
        ]
    
        poller = client.begin_analyze_healthcare_entities(documents)
        result = poller.result()
    
        docs = [doc for doc in result if not doc.is_error]
    
        for idx, doc in enumerate(docs):
    
            ent=set()
            for entity in doc.entities:
                if entity.category=='MedicationName':
                    ent.add(entity.text)
    
            meds=[]
            for relation in doc.entity_relations:
                if relation.relation_type=='DosageOfMedication':
                    k=['name','dosage','score']
                    for role in relation.roles:
                        if role.name=='Medication':
                            k[0]=role.entity.text
                        if role.name=='Dosage':
                            k[1]=role.entity.text
                            k[2]=role.entity.confidence_score
                    if k[0] in ent:
                        meds.append(k)
    
            for med in ent:
                meds.append([med,'unknown',0])
    
            meds.sort(key=lambda x:x[2])
    
            check=set()
            for each in meds[::-1]:
                if each[0] not in check:
                #print("Medicine {} with dosage {}".format(each[0],each[1]))
                    output.append("\nMedicine {} with dosage {} \n".format(each[0],each[1]))
                    final_text+="\nMedicine {} with dosage {} \n".format(each[0],each[1])
                    check.add(each[0])
        return output
    
    final_text=""
    output=[]
    client = authenticate_client()
    output+=entity_recognition_example(client)
    output+=health_example(client)
    return output


if __name__ == "__main__":
    app.run(port=5001)