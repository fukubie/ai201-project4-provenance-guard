# Planning Specification: Provenance Guard

## Architecture Narrative

### 1. The Submission Flow (POST /submit)
    The creator sends text to /submit endpoint
    The endpoint passes this raw text simultaneously to Signal 1 (Groq LLM) and Signal 2 (Stylometric Heuristics).
    The engine takes both individual numbers, calculates a weighted average, and produces a final `confidence` score between 0.0 and 1.0.
    The score passes through a threshold rules to generate a `transparency label`.
    The system generates a unique content_id, bundles all scores, labels, and timestamps together, and appends them as a new row in a local Audit Log.
    The user receives a clean JSON response.
### 2. The Appeal Flow (POST /appeal)
    A creator provides a content_id and their explanation text (creator_reasoning) to the /appeal endpoint.
    The system searches the Audit Log for that specific ID, changes its status field from "classified" to "under_review", and attaches the explanation text.
    The user receives a confirmation message.

## Two Signals & Blind Spots
    
### Groq LLM Semantic Assessment
    It measures sentence flow, word transitions, semantic structure, and repetitive phrases commonly favored by LLMs (like "Furthermore," "It is important to note," or "In conclusion").
    It works because AI text defaults to predictable, highly generic patterns.
    Its Blind Spot: It fails to detect heavily edited AI text, or human writers who naturally write in a formal, dry, corporate style.
### Stylometric Sentence Length Variance (Pure Python)
    It measures the mathematical standard deviation of a sentence lengths across the text.
    It works because AI models prioritize uniform sentence lengths. Humans naturally vary their pace, writing short, punchy fragments alongside lengthy, descriptive sentences.
    Its Blind Spot: Short text blocks (like a short poem or a tweet) do not provide enough sentences to generate a statistically meaningful mathematical variance.

## Architecture Flow

### Submission Flow
```mermaid
graph TD
    %% Style definitions
    classDef endpoint fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef storage fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;

    %% Submission Flow
    subgraph SubmissionFlow [POST /submit]
        direction TD
        
        A[User Text Content] --> B(POST /submit)
        
        %% Chained visually to force a single vertical column
        B -->|Trigger Parallel Signals| C[Signal 1: Groq LLM Semantic Assessment]
        C --> D[Signal 2: Python Stylometric Variance]
        
        D -->|Combine Scores 0-1| E[Ensemble Scorer]
        
        E -->|Combined Score| F[UX Label Router]
        F -->|Human-Readable Label| G[(Structured Audit Log)]
        G --> H[JSON Response back to User]
    end
    
    %% Apply Classes
    class B endpoint;
    class C,D,E,F process;
    class G storage;
```
### Appeal Flow

```mermaid
graph TD
    %% Style definitions
    classDef endpoint fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef storage fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;

    %% Appeal Flow
    subgraph AppealFlow [POST /appeal]
        direction TD
        
        I[Creator Reasoning & Content ID] --> J(POST /appeal)
        J --> K[Log Database Lookup]
        K --> L[Update Status to 'under_review']
        L --> M[Append Appeal to Audit Log]
        M --> N[JSON Confirmation Response]
    end

    %% Apply Classes
    class J endpoint;
    class K,L process;
    class M storage;
```