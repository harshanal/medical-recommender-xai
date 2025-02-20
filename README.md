# Explainable Medical Recommendation Engine (OWL + LLM Inference)

This project implements a simplified medical recommendation engine, enhanced with the OpenAI API.

## Features

*   **OWL Ontology:** Uses an OWL file (`ontology.owl`) for the knowledge base.
*   **`rdflib`:** Uses `rdflib` for ontology processing.
*   **SPARQL Queries:** Employs SPARQL for retrieving information.
*   **OpenAI API Integration:**
    *   **Natural Language Input:** Understands free-form text input and maps it to ontology concepts.
    *   **Enhanced Explanations:** Generates more natural and detailed explanations.
    *   **Unknown Concept Handling:** Provides helpful responses even for concepts not in the ontology.
*   **Explainability:** Focuses on providing clear, understandable explanations for recommendations.
*   **Ranking:** Ranks recommendations based on ontology connections.

## Files

*   `ontology.owl`: The medical ontology (OWL/TTL).
*   `main.py`: The main Python script.
*   `.env`: (Optional, but recommended) A file to store your OpenAI API key.

## How to Run

1.  **Install Dependencies:**
    ```bash
    pip install rdflib openai python-dotenv
    ```

2.  **Set up API Key:**
    *   Create a `.env` file in the project directory.
    *   Add your OpenAI API key to the `.env` file:
        ```
        OPENAI_API_KEY=your_api_key_here
        ```
    *   **Alternatively**, you can set the `OPENAI_API_KEY` environment variable directly in your system.

3.  **Run the Script:**
    ```bash
    python main.py
    ```

4.  **Enter Concepts/Questions:**  You can now enter free-form text, not just exact concept names.

## Example Usage