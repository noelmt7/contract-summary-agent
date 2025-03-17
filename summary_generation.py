from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.workflow import Workflow, RunResponse, RunEvent
from config.constants import (
    TEMPLATE_PARSER_SYSTEM_PROMPT, 
    SUMMARY_GENERATION_SYSTEM_PROMPT, 
    EDITOR_SYSTEM_PROMPT, 
    NER_SYSTEM_PROMPT  # Add a new system prompt for NER
)
from textwrap import dedent
from typing import Iterator

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

    ner_agent: Agent = Agent(
        name="NER Agent",
        model=OpenAIChat(id="gpt-4o", temperature=0.2, top_p=0.9),
        system_prompt=NER_SYSTEM_PROMPT,
        structured_outputs=True,
    )

    template_parser_agent: Agent = Agent(
        name="Template Parser Agent",
        model=OpenAIChat(id="gpt-4o", temperature=0.2, top_p=0.9),
        system_prompt=TEMPLATE_PARSER_SYSTEM_PROMPT,
        structured_outputs=True,
    )

    summary_agent: Agent = Agent(
        name="Summary Agent",
        model=OpenAIChat(id="gpt-4o", temperature=0.2, top_p=0.9),
        system_prompt=SUMMARY_GENERATION_SYSTEM_PROMPT,
        structured_outputs=True,
    )

    editor_agent: Agent = Agent(
        name="Editor Agent",
        model=OpenAIChat(id="gpt-4o", temperature=0.2, top_p=0.9),
        system_prompt=EDITOR_SYSTEM_PROMPT,
        markdown=True,
    )

    def run(self, tender_text: str, template_text: str) -> Iterator[RunResponse]:
        
        # Step 1: Extract Named Entities using AI
        ner_message = dedent(f"""
        Extract key entities from the following tender document. Identify:
        - Organization Names
        - Dates
        - Financial Figures
        - Locations
        - Legal Terms
        - Persons Mentioned

        **Tender Document:**
        {tender_text}
        """)

        ner_response = self.ner_agent.run(message=ner_message, stream=False)
        extracted_entities = ner_response.content  # AI-extracted entities

        # Step 2: Parse the Template
        template_parser_message = dedent(f"""
        Given the following template text, extract relevant fields required for summarization.

        **Template Provided:**
        {template_text}

        **Extracted Entities from Tender:**
        {extracted_entities}

        Identify key fields that should be included in the summary based on this template.
        """)

        parsed_response = self.template_parser_agent.run(message=template_parser_message, stream=False)
        parsed_template = parsed_response.content

        # Step 3: Generate Summary
        summary_message = dedent(f""" 
        Using the extracted entities and the template structure, generate a structured summary.

        **Template Fields:**
        {parsed_template}

        **Extracted Entities:**
        {extracted_entities}

        Ensure the summary follows the structure of the provided template.
        """)
        
        summary_response = self.summary_agent.run(message=summary_message, stream=False)
        summary_draft = summary_response.content

        # Step 4: Edit Summary for Clarity & Readability
        editor_message = dedent(f"""
        Review and refine the following summary for clarity, conciseness, and professionalism.

        **Generated Summary:**
        {summary_draft}

        **Editing Guidelines:**
        - Ensure clarity, accuracy, and professionalism.
        - Improve grammar, readability, and formatting.
        - Remove redundancy while maintaining all key details.
        """)

        editor_response = self.editor_agent.run(message=editor_message, stream=False)
        edited_summary = editor_response.content

        yield RunResponse(content=edited_summary, event=RunEvent.workflow_completed)
