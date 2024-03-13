# Design

## Description

### Goal

ML-Tutor will be an Anki add-on that will use generative AI to rephrase the Anki cards in order to ask the question
in a slightly different way. This is done in order to avoid having the user associate the answer of the question to
the specific formulation of the question, rather than the semantic content of the question.

### User Specifications

- The add-on will use LLM to rephrase the original note and will show that to the user.
- When the user clicks the button to show the answer, the original note will be shown as well.
- The add-on will work only for regular and cloze deletion cards.
- The add-on will default to ChatGPT as the generative AI model.
  - Should be able to choose 3.5 vs 4.0 from the start
- Perhaps there should be a way to determine if it's a good idea to rephrase the note, or at least a way to
  let the LLM tell you when the note is ambiguous and cannot be rephrased properly (investigate)

### Technical Specifications

- It must be developed with the idea to easily replace the generative AI model with another one (modular).
- Ideally (investigate), it must prefetch the generated notes in order to avoid the user waiting for the note to be
  generated.
  - It could pre-fetch one note ahead.
- It should also cache the generated notes in main memory in order to operate smoothly on "undo" and "redo" operations.