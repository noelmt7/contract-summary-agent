from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow, RunResponse, RunEvent
from config.constants import TEMPLATE_PARSER_SYSTEM_PROMPT, SUMMARY_GENERATION_SYSTEM_PROMPT, EDITOR_SYSTEM_PROMPT
from textwrap import dedent
from typing import Dict, Any, Iterator

import spacy  # Move import to the right place

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def ner_extraction(tender_text: str) -> dict:
    """
    Extract key entities from the tender document using spaCy.
    
    Args:
        tender_text (str): The contract or tender document text.
    
    Returns:
        dict: Extracted entities such as organization names, dates, monetary amounts, locations, persons, and key terms.
    """
    doc = nlp(tender_text)

    entities = {
        "organization_names": [],
        "dates": [],
        "money": [],
        "terms": [],
        "locations": [],
        "persons": []
    }

    for ent in doc.ents:
        if ent.label_ == "ORG":
            entities["organization_names"].append(ent.text)
        elif ent.label_ == "DATE":
            entities["dates"].append(ent.text)
        elif ent.label_ == "MONEY":
            entities["money"].append(ent.text)
        elif ent.label_ == "GPE":
            entities["locations"].append(ent.text)
        elif ent.label_ == "PERSON":
            entities["persons"].append(ent.text)
        elif ent.label_ in ["LAW", "NORP", "PRODUCT"]:
            entities["terms"].append(ent.text)

    return entities  # Moved outside the loop to process all entities properly

def generate_summary(
        tender_text: str,
        template_text: str
) -> str:
    """
    Generate a structured summary of the contract or tender document based on a template and extracted entities.
    
    Args:
        tender_text (str): The contract or tender document text.
        template_text (str): The template document text.
        entities (dict): Extracted entities such as organization names, dates, monetary amounts, locations, persons, and key terms.
    
    Returns:
        str: A structured summary of the contract or tender document.
    """
    workflow = SummaryGenerationWorkflow()
    for response in workflow.run(
        tender_text=tender_text,
        template_text=template_text
    ):
        if response.content:
            return response.content
        
    raise ValueError("No Summary Generated")


class SummaryGenerationWorkflow(Workflow):

    template_parser_agent: Agent = Agent(
        name = "Template Parser Agent",
        model = OpenAIChat(id="gpt-4o", temperature=0.2, top_p = 0.9),
        system_prompt = TEMPLATE_PARSER_SYSTEM_PROMPT,
        structured_outputs=True,
    )

    summary_agent: Agent = Agent(
        name = "Summary Agent",
        model = OpenAIChat(id="gpt-4o", temperature=0.2, top_p = 0.9),
        system_prompt = SUMMARY_GENERATION_SYSTEM_PROMPT,
        structured_outputs=True,
    )

    editor_agent: Agent = Agent(
        name = "Editor Agent",
        model = OpenAIChat(id="gpt-4o", temperature=0.2, top_p = 0.9),
        system_prompt = EDITOR_SYSTEM_PROMPT,
        markdown=True,
    )

    def run(
        self,
        tender_text: str,
        template_text: str, 

    ) -> Iterator[RunResponse]:
        
        extracted_entities = ner_extraction(tender_text)

        # Step 2: Parse the Template
        template_parser_message = dedent(f"""
        Given the following template text, extract relevant fields required for summarization.

        **Template Provided:**
        {template_text}

        **Extracted Entities from Tender:**
        - Organization Names: {", ".join(extracted_entities["organization_names"])}
        - Dates: {", ".join(extracted_entities["dates"])}
        - Financial Figures: {", ".join(extracted_entities["money"])}
        - Locations: {", ".join(extracted_entities["locations"])}
        - Legal Terms: {", ".join(extracted_entities["terms"])}
        - Persons Mentioned: {", ".join(extracted_entities["persons"])}

        Identify key fields that should be included in the summary based on this template.
        """)

        parsed_response = self.template_parser_agent.run(message = template_parser_message, stream = False)
        parsed_template = parsed_response.content

        # Step 3: Generate Summary
        summary_message = dedent(f""" Using the extracted entities and the template structure, generate a structured summary.
                                 **Template Fields:**
                                 {parsed_template}
                                 **Extracted Entities:**
                                 {template_parser_message}

        Ensure the summary follows the structure of the provided template.
        """)
        summary_response = self.summary_agent.run(message = summary_message, stream = False)
        summary_draft = summary_response.content

        editor_message = dedent(f"""
        Review and refine the following summary for clarity, conciseness, and professionalism.

        **Generated Summary:**
        {summary_draft}

        **Editing Guidelines:**
        - Ensure clarity, accuracy, and professionalism.
        - Improve grammar, readability, and formatting.
        - Remove redundancy while maintaining all key details.
        """)

        editor_response = self.editor_agent.run(message = editor_message, stream = False)
        edited_summary = editor_response.content

        yield RunResponse(content=edited_summary, event = RunEvent.workflow_completed)




