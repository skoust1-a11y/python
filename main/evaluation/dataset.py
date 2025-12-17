"""
Evaluation Dataset Creation Module
Creates and manages evaluation datasets in Langfuse.

TODO: Implement the functions below to create evaluation datasets in Langfuse.
"""

import os
from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables
load_dotenv()


def get_langfuse_client() -> Langfuse:
    """
    Initialize Langfuse client using environment variables.
    
    TODO: Get LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, and LANGFUSE_HOST from environment.
    Validate keys are present, then return Langfuse client initialized with these credentials.
    """
    # TODO: Implement this function
    pass


def create_dataset(langfuse: Langfuse, dataset_name: str):
    """
    Create an evaluation dataset for the RAG system.
    
    TODO: Call langfuse.create_dataset() with name, description, and metadata.
    Metadata should include: sprint="C3-S09", type="product_manual_qa", version="1.0", knowledge_base="product_manual"
    """
    # TODO: Implement this function
    pass


def add_items(langfuse: Langfuse, dataset_name: str):
    """
    Add test cases to the dataset.
    
    TODO: 
    1. Create a list of 10 test cases (3 easy, 4 medium, 3 hard) based on product manual document.
    2. Each test case should have: input (question), expected (answer), category, difficulty, manual_section.
    3. For hard questions, add edge_case field.
    4. Loop through test cases and call langfuse.create_dataset_item() for each.
    5. Build metadata dict with category, difficulty, manual_section, source="product_manual", and edge_case if present.
    """
    # TODO: Implement this function
    test_cases = [
        # TODO: Add 10 test cases (3 easy, 4 medium, 3 hard)
    ]
    
    # TODO: Loop through test_cases and add each to Langfuse dataset
    pass


def main():
    """
    Main function to create the evaluation dataset.
    
    TODO: 
    1. Set DATASET_NAME = "product_manual"
    2. Get Langfuse client, create dataset, add items
    3. Print summary with dataset name, total questions, and breakdown
    """
    # TODO: Implement this function
    pass


if __name__ == "__main__":
    main()
