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
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not secret_key or not public_key:
        raise ValueError(
            "LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY must be set in the environment"
        )

    return Langfuse(
        secret_key=secret_key,
        public_key=public_key,
        host=host,
    )


def create_dataset(langfuse: Langfuse, dataset_name: str):
    """
    Create an evaluation dataset for the RAG system.
    
    TODO: Call langfuse.create_dataset() with name, description, and metadata.
    Metadata should include: sprint="C3-S09", type="product_manual_qa", version="1.0", knowledge_base="product_manual"
    """
    # TODO: Implement this function
    dataset = langfuse.create_dataset(
        name=dataset_name,
        description="Evaluation dataset for the Product Manual RAG system (CloudSync Pro User Manual)",
        metadata={
            "sprint": "C3-S09",
            "type": "product_manual_qa",
            "version": "1.0",
            "knowledge_base": "product_manual",
        },
    )
    return dataset


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
        # --- Easy (3) ---
        {
            "input": "What are the system requirements for CloudSync Pro?",
            "expected": (
                "CloudSync Pro requires Windows 10 or later, macOS 10.15 or later, or a "
                "Linux distribution based on Ubuntu 18.04 or newer. It needs a minimum of "
                "4GB RAM, 500MB of free disk space, and an active internet connection with at "
                "least 5 Mbps download and 2 Mbps upload speeds. Mobile support requires iOS "
                "13.0 or later and Android 8.0 or later."
            ),
            "category": "installation",
            "difficulty": "easy",
            "manual_section": "1. Getting Started and Installation",
        },
        {
            "input": "How much storage does the free plan include?",
            "expected": (
                "The free plan includes 5GB of cloud storage, basic file synchronization, "
                "access to web and mobile apps, sharing with up to 5 people, and 30 days of "
                "version history."
            ),
            "category": "storage",
            "difficulty": "easy",
            "manual_section": "6. Storage Plans and Limits",
        },
        {
            "input": "How long does the CloudSync Pro installation typically take?",
            "expected": (
                "The installation typically takes 2-5 minutes depending on system "
                "performance."
            ),
            "category": "installation",
            "difficulty": "easy",
            "manual_section": "1. Getting Started and Installation",
        },
        # --- Medium (4) ---
        {
            "input": "How do I set up two-factor authentication on CloudSync Pro?",
            "expected": (
                "Two-factor authentication can be set up using authenticator apps such as "
                "Google Authenticator, Microsoft Authenticator, or Authy by scanning a QR code "
                "and entering a verification code. SMS-based 2FA is also available as an "
                "alternative, though app-based authentication is more secure. Once enabled, "
                "both a password and a time-based code are required when signing in from new "
                "devices."
            ),
            "category": "authentication",
            "difficulty": "medium",
            "manual_section": "2. Account Setup and Authentication",
        },
        {
            "input": "What encryption standard does CloudSync Pro use for end-to-end encryption?",
            "expected": (
                "CloudSync Pro's end-to-end encryption uses AES-256 encryption, the industry "
                "standard for secure data protection. Files are encrypted on the user's device "
                "before upload so only the user (or those with the encryption key) can decrypt "
                "them."
            ),
            "category": "security",
            "difficulty": "medium",
            "manual_section": "5. Security and Privacy Settings",
        },
        {
            "input": "How long is version history retained across the different plans?",
            "expected": (
                "Version history is retained for 30 days on free plans, 90 days on paid plans, "
                "and indefinitely (unlimited) on enterprise plans."
            ),
            "category": "collaboration",
            "difficulty": "medium",
            "manual_section": "4. Collaboration and Sharing",
        },
        {
            "input": "How much does the Personal Pro plan cost and what does it include?",
            "expected": (
                "The Personal Pro plan costs $9.99 per month or $99.99 per year (saving 17%). "
                "It includes 1TB of cloud storage, priority customer support, 90 days of "
                "version history, advanced sharing features, no file size limits, early access "
                "to new features, and sharing with up to 25 people."
            ),
            "category": "storage",
            "difficulty": "medium",
            "manual_section": "6. Storage Plans and Limits",
        },
        # --- Hard (3) ---
        {
            "input": "If I edit the same file on two different devices at the same time, what happens?",
            "expected": (
                "When the same file is modified on multiple devices simultaneously, CloudSync "
                "Pro automatically creates conflict copies with timestamps and device names "
                "appended. Users are notified of conflicts and can choose which version to "
                "keep, merge changes manually, or keep both versions, and a conflict "
                "resolution wizard helps compare versions side-by-side."
            ),
            "category": "synchronization",
            "difficulty": "hard",
            "manual_section": "3. File Synchronization Features",
            "edge_case": "simultaneous_edit_conflict",
        },
        {
            "input": "Can CloudSync Pro administrators access my end-to-end encrypted files?",
            "expected": (
                "No. When end-to-end encryption is enabled, files are encrypted on the user's "
                "device before upload, and only the user (or users with the encryption key) "
                "can decrypt and access them. Even CloudSync Pro administrators cannot access "
                "E2EE-protected files."
            ),
            "category": "security",
            "difficulty": "hard",
            "manual_section": "5. Security and Privacy Settings",
            "edge_case": "admin_cannot_access_e2ee",
        },
        {
            "input": "How many members can a team folder have, and does the limit depend on the plan?",
            "expected": (
                "Team folders support up to 100 members on standard plans and unlimited "
                "members on enterprise plans."
            ),
            "category": "collaboration",
            "difficulty": "hard",
            "manual_section": "4. Collaboration and Sharing",
            "edge_case": "plan_based_member_limit",
        },
    ]

    # TODO: Loop through test_cases and add each to Langfuse dataset
    for case in test_cases:
        metadata = {
            "category": case["category"],
            "difficulty": case["difficulty"],
            "manual_section": case["manual_section"],
            "source": "product_manual",
        }
        if "edge_case" in case:
            metadata["edge_case"] = case["edge_case"]

        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            input=case["input"],
            expected_output=case["expected"],
            metadata=metadata,
        )

    return test_cases


def main():
    """
    Main function to create the evaluation dataset.
    
    TODO: 
    1. Set DATASET_NAME = "product_manual"
    2. Get Langfuse client, create dataset, add items
    3. Print summary with dataset name, total questions, and breakdown
    """
    # TODO: Implement this function
    DATASET_NAME = "product_manual"

    langfuse = get_langfuse_client()
    create_dataset(langfuse, DATASET_NAME)
    test_cases = add_items(langfuse, DATASET_NAME)

    langfuse.flush()

    easy = sum(1 for c in test_cases if c["difficulty"] == "easy")
    medium = sum(1 for c in test_cases if c["difficulty"] == "medium")
    hard = sum(1 for c in test_cases if c["difficulty"] == "hard")

    print("=" * 50)
    print("Evaluation Dataset Created")
    print("=" * 50)
    print(f"Dataset name   : {DATASET_NAME}")
    print(f"Total questions: {len(test_cases)}")
    print(f"  - Easy       : {easy}")
    print(f"  - Medium     : {medium}")
    print(f"  - Hard       : {hard}")
    print("=" * 50)


if __name__ == "__main__":
    main()
