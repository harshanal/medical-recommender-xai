import rdflib
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL
import openai
import os
from dotenv import load_dotenv

# Load API Key 
load_dotenv()  
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("OpenAI API key not found.  Set the OPENAI_API_KEY environment variable.")

def load_ontology(filepath="ontology.owl"):
    """Loads the ontology from an OWL file."""
    g = Graph()
    g.parse(filepath, format="turtle")
    return g

def get_concept_uri(graph, concept_name, ontology_ns):
    """Gets the URI of a concept, handling case-insensitivity."""
    # Check for exact match first (case-sensitive)
    concept_uri = ontology_ns[concept_name]
    if (concept_uri, RDF.type, OWL.Class) in graph:
        return concept_uri

    # Case-insensitive search
    for s, p, o in graph.triples((None, RDF.type, OWL.Class)):
        if str(s).replace(str(ontology_ns), "").lower() == concept_name.lower():
            return s
    return None

def get_related_concepts(graph, concept_uri, rel_type_uri=None):
    """Retrieves related concepts (same as before)."""
    related_concepts = []
    if rel_type_uri:
        query = f"""
            SELECT ?relatedConcept
            WHERE {{
                {{ <{concept_uri}> <{rel_type_uri}> ?relatedConcept . }}
                UNION
                {{ ?relatedConcept <{rel_type_uri}> <{concept_uri}> . }}
            }}
        """
        results = graph.query(query)
        for row in results:
            related_concepts.append(row.relatedConcept)
    else:
        query = f"""
            SELECT ?relatedConcept ?relType
            WHERE {{
                {{ <{concept_uri}> ?relType ?relatedConcept . }}
                UNION
                {{ ?relatedConcept ?relType <{concept_uri}> . }}
            }}
        """
        results = graph.query(query)
        for row in results:
            if row.relatedConcept != concept_uri:
                related_concepts.append(row.relatedConcept)

    return related_concepts

def generate_explanation(graph, concept_uri, related_concept_uri):
    """Generates explanations (basic - will be enhanced by LLM)."""
    query = f"""
        SELECT ?relType
        WHERE {{
            {{ <{concept_uri}> ?relType <{related_concept_uri}> . }}
            UNION
            {{ <{related_concept_uri}> ?relType <{concept_uri}> . }}
        }}
    """
    results = graph.query(query)
    for row in results:
        rel_type = row.relType
        rel_type_str = str(rel_type).replace("http://example.org/medical_ontology#", "")
        concept_str = str(concept_uri).replace("http://example.org/medical_ontology#", "")
        related_concept_str = str(related_concept_uri).replace("http://example.org/medical_ontology#", "")

        if rel_type_str == "subClassOf":
            if (concept_uri, RDFS.subClassOf, related_concept_uri) in graph:
                 return f"{concept_str} is a subclass of {related_concept_str}."
            else:
                return f"{related_concept_str} is a subclass of {concept_str}."
        elif rel_type_str == "hasSymptom":
            return f"{related_concept_str} is a symptom of {concept_str}."
        elif rel_type_str == "treatedBy":
            return f"{related_concept_str} is a treatment for {concept_str}."
        elif rel_type_str == "treats":
            return f"{related_concept_str} treats {concept_str}."
    return "No direct relationship found."

def rank_concepts(graph, related_concepts):
    """Ranks concepts (same as before)."""
    def get_degree(concept_uri):
        query = f"""
            SELECT (count(?rel) as ?degree)
            WHERE {{
              {{ <{concept_uri}> ?rel ?o }}
              UNION
              {{ ?s ?rel <{concept_uri}> }}
            }}
        """
        result = graph.query(query)
        return int(list(result)[0][0])

    return sorted(related_concepts, key=get_degree, reverse=True)


def map_input_to_concept(graph, user_input, ontology_ns):
    """Uses the LLM to map free-form text to a concept URI."""
    prompt = f"""
    You are a medical terminology expert.  Given the following user input, identify the most relevant medical concept from this list of concepts:
    {', '.join([str(s).replace(str(ontology_ns), "") for s, _, _ in graph.triples((None, RDF.type, OWL.Class))])}.
    If none of the concepts are relevant, respond with 'None'.

    User Input: {user_input}
    Relevant Concept:
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o",  
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": prompt}],
        temperature=0.0,  # Low temperature for more deterministic output
        max_tokens=50 #Keep it brief
    )
    concept_name = response.choices[0].message['content'].strip()

    if concept_name.lower() == "none":
        return None
    return get_concept_uri(graph, concept_name, ontology_ns)

def generate_llm_explanation(concept_str, related_concept_str, basic_explanation):
    """Uses the LLM to enhance and expand the explanation."""
    prompt = f"""
    You are a medical expert explaining the relationship between medical concepts.
    Given the following information:

    Concept: {concept_str}
    Related Concept: {related_concept_str}
    Basic Relationship: {basic_explanation}

    Provide a clear and concise explanation of the relationship between these concepts,
    suitable for a patient with limited medical knowledge.  Keep it brief (under 50 words).
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,  # Slightly higher temperature for more varied explanations
        max_tokens=100
    )
    return response.choices[0].message['content'].strip()

def handle_unknown_concept(user_input):
    """Uses the LLM to provide a response for unknown concepts."""
    prompt = f"""
    You are a helpful medical assistant.  A user has asked about the following:

    User Input: {user_input}

    This concept is not in your current knowledge base.  Provide a brief, general response,
    and suggest that the user consult a medical professional for more specific information.
    """
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message['content'].strip()


def recommend(graph, concept_uri, user_input):
    """Provides recommendations and explanations, using LLM for enhancements."""
    recommendations = {}
    all_related = get_related_concepts(graph, concept_uri)
    ranked_related = rank_concepts(graph, all_related)

    for related_concept_uri in ranked_related:
        basic_explanation = generate_explanation(graph, concept_uri, related_concept_uri)
        if basic_explanation:
            concept_str = str(concept_uri).replace("http://example.org/medical_ontology#", "")
            related_concept_str = str(related_concept_uri).replace("http://example.org/medical_ontology#", "")
            llm_explanation = generate_llm_explanation(concept_str, related_concept_str, basic_explanation)
            recommendations[related_concept_str] = llm_explanation
    return recommendations

def main():
    """Main function."""
    graph = load_ontology()
    ontology_ns = Namespace("http://example.org/medical_ontology#")

    while True:
        user_input = input("Enter a medical concept or question (or 'q' to quit): ").strip()
        if user_input.lower() == 'q':
            break

        concept_uri = map_input_to_concept(graph, user_input, ontology_ns)

        if concept_uri:
            recommendations = recommend(graph, concept_uri, user_input)
            if recommendations:
                print("\nRecommendations:")
                for related_concept, explanation in recommendations.items():
                    print(f"- {related_concept}: {explanation}")
            else:
                print("No recommendations found for this concept within the ontology.")
        else:
            # Handle unknown concept using LLM
            response = handle_unknown_concept(user_input)
            print("\nResponse:")
            print(response)

        print("-" * 20)

if __name__ == "__main__":
    main()