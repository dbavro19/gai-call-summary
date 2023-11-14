import boto3
import json
import botocore
import streamlit as st
import time
import requests


### Title displayed on the Streamlit Web App
st.set_page_config(page_title="Call Summary", page_icon=":tada", layout="wide")


#Header and Subheader dsiplayed in the Web App
with st.container():
    st.header("Analyize Audio with Generative AI")
    st.subheader("")
    st.title("Customer Support Call Summarization")

#Upload Audio File
uploaded_file = st.file_uploader("Choose a file")

temp_transcription=[]


#Invoke LLM - Bedrock - Creates the Docuemnt based on user feedback
def invoke_llm_summary(bedrock, transcript):

    print("TESTING TRANSCRIPTION IN INVOKE")
    print(transcript)




    template="""
Full Call Log: 
(Full text of the Call transcription broken up line by line by speaker - Each line should be sperarted by a new line )
[EXAMPLE]
Customer Support Agent: (Call Text)
Customer: (Call Text)
Customer Support Agent: (Call Text)
[etc.]
[/EXAMPLE]

###

Customer Support Agent Name: (Name of the Customer Support Agent, "Not Provided" of name is not provided)

Cusotmer Name: (Name of the Customer, "Not Provided" of name is not provided)

Customer Issue: (Detailed Summary of the Customer Issue)

Actions Taken: (Detailed Summary of the Actions Taken)

Resolution: (Summary of the Resolution)

Sentiment Analysis: (Provide a Sentiment Analysis of the Cusotmers Sentiament based on the result of the call. Should be one of Positive, Mixed, Negative)"""

# Uses the Bedrock Client, the user input, and the document template as part of the prompt


    ##Setup Prompt
    prompt_data = f"""

Human:

Generate a summary of the customer support phone call provided in the <call_transcript> XML tags
Your repsonse should follow the format and structure of the provided template
Base your response soley on the content of the call transcript, dont make too many assumptions
Response should be in valid markdown format, Section Titles should be Bold

###

<Call_Transcript>
{transcript}
</Call_Transcript>

<Output_Template>
{template}
</Output_Template>

###

Assistant: Here is a summary of the call

"""
#Add the prompt to the body to be passed to the Bedrock API
#Also adds the hyperparameters 

    body = json.dumps({"prompt": prompt_data,
                 "max_tokens_to_sample":5000,
                 "temperature":.2,
                 "stop_sequences":[]
                  }) 
    
    #Run Inference
    modelId = "anthropic.claude-v2"  # change this to use a different version from the model provider if you want to switch 
    accept = "application/json"
    contentType = "application/json"
    #Call the Bedrock API
    response = bedrock.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )

    #Parse the Response
    response_body = json.loads(response.get('body').read())
    llmOutput=response_body.get('completion')

    print(llmOutput)

    #Return the LLM response
    return llmOutput



def generate_summary(transcript):

    #Setup bedrock client
    bedrock = boto3.client('bedrock-runtime' , 'us-east-1', endpoint_url='https://bedrock.us-east-1.amazonaws.com')

    #invoke LLM
    llmOutput = invoke_llm_summary(bedrock, transcript)
    return llmOutput



def transcribe_file(object_name):

    transcribe_client = boto3.client('transcribe')

    file_uri= f"s3://dbavaro-landing-bucket/{object_name}"
    job_name=object_name+time.strftime("%Y%m%d-%H%M%S")
    full_transcript=""

    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': file_uri},
        #MediaFormat='wav',
        LanguageCode='en-US'
    )

    max_tries = 60
    while max_tries > 0:
        max_tries -= 1
        job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = job['TranscriptionJob']['TranscriptionJobStatus']
        if job_status in ['COMPLETED', 'FAILED']:
            print(f"Job {job_name} is {job_status}.")
            if job_status == 'COMPLETED':
                print(
                    f"Download the transcript from\n"
                    f"\t{job['TranscriptionJob']['Transcript']['TranscriptFileUri']}.")
                
                job_result = requests.get(
                    job['TranscriptionJob']['Transcript']['TranscriptFileUri']).json()
                full_transcript=job_result['results']['transcripts'][0]['transcript']


                return full_transcript
            break
        else:
            print(f"Waiting for {job_name}. Current status is {job_status}.")
        time.sleep(10)



def upload_to_s3(file_name, object_name):
    bucket="dbavaro-landing-bucket"


    s3 =boto3.client('s3')
    response = s3.upload_fileobj(file_name, bucket, object_name)

    return object_name

object_name=""


#Create Buttons and start workflow upon "Submit"
result=st.button("Upload File and Get Summary")
if result:
    filename= uploaded_file.name
    # Upload to S3
    object_name=upload_to_s3(uploaded_file, filename)
    transcription = transcribe_file(object_name)
    temp_transcription.append(transcription)

    llm_response=generate_summary(temp_transcription[-1])
    st.markdown(llm_response)

#    result2=st.button("Get Call Summary")
#    if result2:
#        print("Testing")
#        print(temp_transcription[-1])
#
#        llm_response= generate_summary(temp_transcription[-1])
#        st.markdown(llm_response)

