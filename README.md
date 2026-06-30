# Provenance Guard

## Architecture Overview
When a creator submits text via `POST /submit`, the text is sent simultaneously to two detection signals: a semantic LLM check (Groq) and a structural variance check (Python stylometrics). The system calculates a weighted ensemble score (65% Groq, 35% Stylometrics) to generate a final confidence score between 0.0 and 1.0. This score routes the text to a specific Transparency Label. Finally, the submission, its scores, and the label are saved to a local audit log, and a unique `content_id` is returned to the user.

## Detection Signals
* **Signal 1: Groq LLM Semantic Assessment:** Measures sentence flow, semantic structure, and generic transitional phrases. 
  * *Blind spot:* Fails to detect human writers who naturally write in a formal, dry, corporate style.
* **Signal 2: Stylometric Sentence Length Variance:** Measures the standard deviation of sentence lengths, mapping high variance (human) to lower scores, and high uniformity (AI) to higher scores. 
  * *Blind spot:* Extremely short text blocks don't provide enough data for a meaningful standard deviation.

## Confidence Scoring
The final score is a weighted ensemble: `(0.65 * Groq Score) + (0.35 * Stylometric Score)`. This prevents false positives. For example, a short AI-generated text might get a high Groq score but a moderate stylometric score due to its short length, pulling the total score down into the "Uncertain" category rather than falsely condemning it.

**High-Confidence AI Example (Score:  0.695):**
> "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders must collaborate."

**High-Confidence Human Example (Score: 0.2147):**
> "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after. my friend got the spicy version and said it was better."

## Transparency Labels
Depending on the final confidence score, users see one of three exact labels:
* **0.00 - 0.39:** "Verified Original: Our system recognizes this text as original, human-crafted creative work."
* **0.40 - 0.75:** "Attribution Unclear: This text contains a blend of structural patterns. We are unable to confidently verify its origin."
* **0.76 - 1.00:** "Generated Content: Our system has detected a high probability of automated or AI-assisted writing patterns within this text."

## Rate Limiting
To prevent abuse while accommodating normal creator workflows, the `POST /submit` endpoint is rate-limited to 10 requests per minute. 

**Evidence of Rate Limiter working (429 Status Codes):**
```text
200
200
200
200
200
200
200
200
200
429
429
429
```
## Known Limitations
The system will likely misclassify non-native English speakers or technical academics. These creators naturally write with highly formalized, structured language and uniform sentence lengths, which our stylometric heuristics will mistakenly flag as AI-generated uniformity. 

## Spec Reflection
* **How the spec helped:** Having the exact threshold rules and weighted math planned out ahead of time made writing the Python ensemble function incredibly fast.
* **How the implementation diverged:** [WRITE ONE SENTENCE HERE ABOUT SOMETHING YOU CHANGED. E.g., We had to add a fallback in the stylometrics function to return 0.5 if the text had fewer than 2 sentences, to handle the blind spot.]

## AI Usage
* **Instance 1:** I prompted Claude Code with my Architecture Narrative and Mermaid diagram to generate the boilerplate Flask app and Groq API call. I reviewed the code to ensure it clamped scores between 0.0 and 1.0.
* **Instance 2:** I provided Claude with my stylometric plan, and it generated a Python function using `statistics.stdev`, applying a clever normalization factor of `15.0` to map the standard deviation to a 0-1 scale.