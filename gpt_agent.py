# gpt_agent.py

import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from logger_setup import logger

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=OPENAI_API_KEY)


def gpt_classify_issue(subject, body):
    prompt = f"""
You are an assistant that classifies emails into JIRA tickets.
Based on the following subject and body, return a JSON object with:
- issueType: "Bug", "Task", or "Story"
- client: Determine the client from Email body - email address or email body. Use the domain part (e.g., oetraining.com → OETraining). Match against this list of known clients: [Global, ALA, AOCDS, APA2118, AWPPW, AWU, BIU, BPSU, CARPDC, CarpentersUnion, CATS831, CFA, CFPA, CMPTCW, CMW, CSCRC, CUPE37, FLCRC, HBPOA, HNA, HOFSTRA, IATSE 887, IATSE 927, IATSE107, IATSE15, IATSE22, IATSE58, IATSE665, IBEW Local 303, IBEW105, IBEW124, IKORCC, IMWU, IUOE18, IUPATDC5, IW377, IWL118, IWL229, IWL29, IWL397, IWL433, IWL732, IWL8, KC249, LACPDU, LBPOA, LEEBA, LEO, Localhire, MCPB, MRCC, NCSRCC, New Payment, New_Grievances, NorCARPENTERS, NWCI, OETraining, OPCMIA528, OPEIU12, OPEIU174, OPEIU29, PNWSU, PNWProfiles, PSEofWA, QUADC, SEBA, SECRC, SEIU87, SWCarpenters, Teamsters264, Teamsters456, Teamsters728, Teamsters817, Teamsters988, TeamstersNAC, TEF, TWU577, TWU579, UA123, UA198, UA230, UA32, UA434, UA467, UA486, UA486School, UA525, UA550, UA798, UA8, USW1331, UWUA1-2, WSCarpenters, WSRJB, N/A, IBEW110, OPEIU8, Teamsters891, UCCWA, IATSE835, NWOBT, IBEW640, IBEW379, ILA2078, IATSE500, CUPE417], if not found - put "N/A"

Email subject: {subject}
Email body: {body}

Respond only with a JSON object, nothing else.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content
        logger.info(f"GPT Response: {content}")
        return json.loads(content)
    except Exception as e:
        logger.error(f"GPT call or JSON parse failed: {e}")
        return None
