import json
import base64
from datetime import date
from config import CLAUDE_CONFIG, NO_REPLY_TYPES, TRANSITIONS
from zoho_api.api import api_request
from html_converter import convert_to_text
from claude import ask_claude_beta, extract_json


def classify_responses(responses):
    message_content = f"""
    Classify the following responses:
    {json.dumps(responses)}
    """
    message_classification_response = ask_claude_beta(
        model="claude-sonnet-5",
        max_tokens=4096,
        message=message_content,
        custom_skills=[CLAUDE_CONFIG['skills']['lead_reply_classifier']],
        betas=['code_execution', 'skills'],
        tools=['code_execution'])
    message_classification_json = extract_json(message_classification_response)
    return message_classification_json


def form_reply_message(responses):
    message_content = f"""
    Generate Responses for the following Emails:
    {json.dumps(responses)}
    """
    message_classification_response = ask_claude_beta(
        model="claude-sonnet-5",
        max_tokens=4096,
        message=message_content,
        custom_skills=[CLAUDE_CONFIG['skills']['response_generator']],
        betas=['code_execution', 'skills'],
        tools=['code_execution'])
    message_classification_json = extract_json(message_classification_response)
    return message_classification_json


def prepare_conversations(responses):
    for response in responses:
        response['contact_message_content'] = convert_to_text(base64.b64decode(response['contact_message_content']).decode("utf-8"))
        for outbound_message in response['kitrum_messages_content']:
            outbound_message['message_content'] = convert_to_text(base64.b64decode(outbound_message['message_content']).decode("utf-8"))
    return responses


def form_classification_payload(prepared_conversations):
    relevant_keys = ['contact_id', "esp_contact_id", "contact_message_content"]
    classification_payload = {"conversations": []}
    for prepared_conversation in prepared_conversations:
        conversation_details = {}
        for relevant_key in relevant_keys:
            conversation_details[relevant_key] = prepared_conversation[relevant_key]
        classification_payload['conversations'].append(conversation_details)
    return classification_payload


def form_generator_payload(prepared_conversations):
    response_generator_payload = []
    for prepared_conversation in prepared_conversations:
        response_required = False
        lead_stage = prepared_conversation['lead_stage']
        not_int_type = prepared_conversation['lead_notinterested_type']
        relevant_types = ['Friendly', 'Middle', 'Redirect', 'Already have vendor', 'Have onsite team']
        if lead_stage == "Interested" or (lead_stage == "Not Interested" and not_int_type in relevant_types):
            response_required = True
        if response_required:
            response_generator_payload.append(prepared_conversation)
    return response_generator_payload


def add_classifications(classified_responses, prepared_conversations):
    classified_responses_dict = {}
    for classified_response in classified_responses['conversations']:
        classified_responses_dict[classified_response['contact_id']] = {"lead_stage": classified_response['lead_stage'], "lead_notinterested_type": classified_response['lead_notinterested_type']}
    for prepared_conversation in prepared_conversations:
        conversation_classification = classified_responses_dict[prepared_conversation['contact_id']]
        prepared_conversation.update(conversation_classification)


def add_ai_responses(generated_ai_responses, prepared_conversations):
    ai_responses_dict = {}
    for generated_ai_response in generated_ai_responses['conversations']:
        ai_responses_dict[generated_ai_response['contact_id']] = {"ai_response": generated_ai_response['ai_response']}
    for prepared_conversation in prepared_conversations:
        conversation_ai_drafts = ai_responses_dict.get(prepared_conversation['contact_id']) or {}
        prepared_conversation.update(conversation_ai_drafts)


def blueprint_update(record_id, module_name, transition_id, data):
    payload = {
        "blueprint": [
            {
                "transition_id": transition_id,
                "data": data
            }
        ]
    }
    response = api_request(
        f"https://www.zohoapis.com/crm/v8/{module_name}/{record_id}/actions/blueprint",
        "zoho_crm",
        "put",
        payload
    )
    print(f"Blueprint Update: {response}")
    return response


def create_task_crm(task_payload):
    response = api_request(
        "https://www.zohoapis.com/crm/v8/Tasks",
        "zoho_crm",
        "post",
        {"data": [task_payload]}
    )
    print(f"Task Response: {response}")
    return response


def process_crm_contact(prepared_conversations):
    for prepared_conversation in prepared_conversations:
        task_payload = {
            "Team_Name": "Lead Generation Team",
            "Type_of_Task": "FU Leads",
            "Subject": "",
            "Assignged_to": "Denys Biletchenko",
            "Priority": "High",
            "Created_date": date.today().strftime("%Y-%m-%d"),
            "Due_Date": date.today().strftime("%Y-%m-%d"),
            "Who_Id": prepared_conversation['contact_id'],
            "Status": "Not Started",
            "$se_module": "Contacts"
        }
        crm_update_data = {}
        lead_stage = prepared_conversation['lead_stage'];
        lead_notinterested_type = prepared_conversation['lead_notinterested_type']

        # UPDATE BLUEPRINT STAGE
        if lead_notinterested_type in NO_REPLY_TYPES:
            transition_id = TRANSITIONS[lead_stage]
            blueprint_update(
                record_id=prepared_conversation['contact_id'],
                module_name="Contacts",
                transition_id=transition_id,
                data={}
            )

        # UPDATE CONTACT DETAILS
        if lead_stage == "Not Interested":
            task_payload['Subject'] = "AI SDR - Send Response to Not Interested Lead"
            if lead_notinterested_type not in NO_REPLY_TYPES:
                ai_draft_response = prepared_conversation.get('ai_response') or None
            else:
                ai_draft_response = None

            optout = True if lead_notinterested_type == "OptOut" else False
            crm_update_data = {
                "Lead_notinterested": lead_notinterested_type,
                "Response_Template": ai_draft_response,
                "Email_Opt_Out": optout,
                "Reply_Date": date.today().strftime("%Y-%m-%d")
            }
            print(crm_update_data)
        else:
            task_payload['Subject'] = f"Process Response from {lead_stage} on {prepared_conversation['channel_of_commuinication']}"

        if crm_update_data:
            contact_update_status = api_request(
                f"https://www.zohoapis.com/crm/v2/Contacts/{prepared_conversation['contact_id']}",
                "zoho_crm",
                "put",
                {'data': [crm_update_data]}
            )
            print(contact_update_status)

        try:
            create_task_crm(task_payload)
        except Exception as e:
            print(f"Error while creating task: {e}")


def worker(responses):
    try:
        prepared_conversations = prepare_conversations(responses)
        classification_payload = form_classification_payload(prepared_conversations)
        print(f"Classifying {len(responses)} Responses")
        classified_responses = classify_responses(classification_payload)
        print(classified_responses)
        add_classifications(classified_responses, prepared_conversations)
        response_generator_payload = form_generator_payload(prepared_conversations)
        if len(classified_responses['conversations']) == 1 and classified_responses['conversations'][0]['lead_stage'] != 'Not Interested':
            print("Currently skipping this lead stage..")
            generated_ai_responses = {"conversations": []}
        else:
            print(f"Generating {len(response_generator_payload)} Responses")
            generated_ai_responses = form_reply_message({"conversations": response_generator_payload}) if response_generator_payload else {"conversations": []}
        add_ai_responses(generated_ai_responses, prepared_conversations)
        process_crm_contact(prepared_conversations)
    except Exception as e:
        print(f"Error: {e}")




