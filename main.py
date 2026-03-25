import os
import base64
import smtplib
import asyncio
from typing import Optional

import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agents import Agent, Runner, ModelSettings, function_tool, trace
from agents.tool import WebSearchTool

app = FastAPI(title="Prescription Checker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set this to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class WebSearchItem(BaseModel):
    query: str = Field(..., description="The exact search query you would input into a search engine.")
    reason: str = Field(..., description="Your reasoning for why this search is important to the query.")

class WebSearchPlan(BaseModel):
    analysis: str = Field(..., description="Detailed analysis of the drugs' constituents based on the extracted drug names.")
    searches: list[WebSearchItem] = Field(..., description="A list of web searches to perform to verify the data.")

class CheckRequest(BaseModel):
    drug_names: str  # comma-separated or free-text list
    email: Optional[str] = None

class FullCheckRequest(BaseModel):
    image_base64: Optional[str] = None   # base64-encoded image
    drug_names: Optional[str] = None     # manual text input
    email: Optional[str] = None

# ─── Tools ───────────────────────────────────────────────────────────────────

@function_tool
def check_drug_interactions(drug_names: list[str]) -> str:
    """
    Takes a list of drug names, fetches their RxCUIs from the NLM API,
    and checks for interactions between every pair of drugs.
    """
    base_url = "https://rxnav.nlm.nih.gov/REST"
    rxcuis = []
    drug_map = {}

    for drug in drug_names:
        response = requests.get(
            f"{base_url}/rxcui.json",
            params={"name": drug, "search": 1}
        ).json()
        try:
            rxcui = response['idGroup']['rxnormId'][0]
            rxcuis.append(rxcui)
            drug_map[rxcui] = drug
        except (KeyError, IndexError):
            return f"Error: Could not find a clinical ID for '{drug}'. It may be an unsupported brand name."

    if len(rxcuis) < 2:
        return "Need at least two recognized drugs to check for interactions."

    interactions_found = []

    for i in range(len(rxcuis)):
        for j in range(i + 1, len(rxcuis)):
            rxcui1 = rxcuis[i]
            rxcui2 = rxcuis[j]

            url = f"{base_url}/interaction/interaction.json?rxcui={rxcui1}&sources=ONCHigh"
            response = requests.get(url).json()

            if 'interactionTypeGroup' not in response:
                url = f"{base_url}/interaction/list.json?rxcuis={rxcui1}+{rxcui2}"
                response = requests.get(url).json()

            if 'fullInteractionTypeGroup' in response:
                for group in response['fullInteractionTypeGroup']:
                    for interaction_type in group['fullInteractionType']:
                        for pair in interaction_type['interactionPair']:
                            pair_rxcuis = [
                                c['minConceptItem']['rxcui']
                                for c in pair['interactionConcept']
                            ]
                            if rxcui1 in pair_rxcuis or rxcui2 in pair_rxcuis:
                                severity = pair.get('severity', 'Unknown')
                                description = pair.get('description', 'No description.')
                                drug1_name = drug_map[rxcui1]
                                drug2_name = drug_map[rxcui2]
                                interactions_found.append(
                                    f"[{drug1_name} + {drug2_name}] "
                                    f"Severity: {severity} — {description}"
                                )

    if not interactions_found:
        return (
            "No known interactions found in the RxNorm database for these drugs.\n"
            "Note: Absence of data does not mean absence of interaction. "
            "Always consult a pharmacist for clinical decisions."
        )

    return "\n".join(interactions_found)


@function_tool
def send_email(email: str, message: str) -> str:
    """Send an email with the prescription check results."""
    try:
        connection = smtplib.SMTP('smtp.gmail.com', 587)
        connection.starttls()
        connection.login(
            os.getenv("EMAIL_ADDRESS", ""),
            os.getenv("PASSWORD_KEY", "")
        )
        full_message = f"Subject: Prescription Check Results\n\n{message}"
        connection.sendmail(
            from_addr=os.getenv("EMAIL_ADDRESS", ""),
            to_addrs=email,
            msg=full_message
        )
        connection.quit()
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

# ─── Agents ──────────────────────────────────────────────────────────────────

HOW_MANY_SEARCHES = 2

extract_text_agent = Agent(
    name="Extract Text Agent",
    instructions=(
        "You are a pharmacist assistant specialized in reading prescriptions. "
        "When given an image encoded in base64, extract ONLY the drug/medication names and dosages. "
        "If the names are brand names, try to convert them to generic names. "
        "If there are multiple A.P.Is that make up a drug, list them all. "
        "List each drug name with its corresponding dosage on a new line. "
        "If you are unsure about a name, flag it with '(uncertain)'. "
        "If no drug names are found in the image, respond with exactly: 'No drug names found in this image.' "
        "If there is no dosage information, respond with 'Dosage not specified' for that drug."
    ),
    model="gpt-4o-mini"
)

research_agent = Agent(
    name="Web Research Agent",
    instructions=(
        f"You are a helpful assistant designed to get the active constituents of drugs in a drug prescription. "
        f"You will be given a list of drug names extracted from a prescription. Your task is to use the tool at your disposal "
        f"to find out the active constituents of these drugs. Output {HOW_MANY_SEARCHES} search queries you would use to find this information on the web, "
        f"along with a detailed analysis of the drugs' constituents based on the extracted drug names."
    ),
    tools=[WebSearchTool(search_context_size="low")],
    model="gpt-4o-mini",
    model_settings=ModelSettings(tool_choice="required"),
    output_type=WebSearchPlan
)

contraindication_agent = Agent(
    name="Contraindication Checker",
    instructions=(
        "You are a contraindication checker. Follow these rules strictly:\n"
        "1. ALWAYS call the check_drug_interactions tool first. Never answer from memory.\n"
        "2. Pass the EXACT list of drug names given to you directly to the tool.\n"
        "3. Report ONLY what the tool returns — do not add, modify, or summarize results.\n"
        "4. If the tool returns no interactions, say exactly: 'No known interactions found in database.'\n"
        "5. Never infer or make up interactions under any circumstances."
    ),
    model="gpt-4o-mini",
    tools=[check_drug_interactions],
    model_settings=ModelSettings(tool_choice="required"),
)

email_agent = Agent(
    name="Email Agent",
    instructions=(
        "You are an assistant that sends emails. You have access to a tool that can send emails. "
        "The input to you will be an email address and a message. "
        "Use the tool to send the message to the email address provided. "
        "Always use the tool and never attempt to send an email without it."
    ),
    model="gpt-4o-mini",
    tools=[send_email],
    model_settings=ModelSettings(tool_choice="required")
)

# ─── Helper runners ──────────────────────────────────────────────────────────

async def extract_drugs_from_image(image_base64: str) -> str:
    result = await Runner.run(
        extract_text_agent,
        input=f"Here is the base64-encoded prescription image: {image_base64}"
    )
    return result.final_output

async def research_drugs(drug_names: str) -> str:
    result = await Runner.run(research_agent, input=drug_names)
    return result.final_output.analysis

async def check_contraindications(drug_names: str) -> str:
    result = await Runner.run(contraindication_agent, input=drug_names)
    return result.final_output

async def send_results_email(email: str, message: str) -> str:
    result = await Runner.run(email_agent, input=f"Send to {email}: {message}")
    return result.final_output

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Prescription Checker API is running"}

@app.post("/extract")
async def extract_from_image(file: UploadFile = File(...)):
    """Extract drug names from an uploaded prescription image."""
    contents = await file.read()
    image_b64 = base64.b64encode(contents).decode("utf-8")
    try:
        extracted = await extract_drugs_from_image(image_b64)
        return {"extracted_drugs": extracted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/research")
async def research_endpoint(req: CheckRequest):
    """Research active constituents of given drugs."""
    try:
        analysis = await research_drugs(req.drug_names)
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/contraindications")
async def contraindications_endpoint(req: CheckRequest):
    """Check drug-drug interactions."""
    try:
        result = await check_contraindications(req.drug_names)
        return {"contraindications": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/full-check")
async def full_check(
    file: Optional[UploadFile] = File(None),
    drug_names: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
):
    """
    Full pipeline: extract (if image provided) → research → contraindication check → optional email.
    """
    results = {}

    # Step 1: Get drug names
    if file:
        contents = await file.read()
        image_b64 = base64.b64encode(contents).decode("utf-8")
        extracted = await extract_drugs_from_image(image_b64)
        results["extracted_drugs"] = extracted
        drug_input = extracted
    elif drug_names:
        drug_input = drug_names
        results["extracted_drugs"] = drug_names
    else:
        raise HTTPException(status_code=400, detail="Provide either an image file or drug names.")

    # Step 2: Research + contraindications in parallel
    research_task = asyncio.create_task(research_drugs(drug_input))
    contraindication_task = asyncio.create_task(check_contraindications(drug_input))

    analysis, contraindications = await asyncio.gather(research_task, contraindication_task)

    results["analysis"] = analysis
    results["contraindications"] = contraindications

    # Step 3: Optional email
    if email:
        summary = (
            f"Prescription Check Results\n\n"
            f"Drugs Identified:\n{drug_input}\n\n"
            f"Drug Analysis:\n{analysis}\n\n"
            f"Contraindications:\n{contraindications}"
        )
        email_result = await send_results_email(email, summary)
        results["email_status"] = email_result

    return results
