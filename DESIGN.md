# Design

## Description

### Goal

ML-Tutor will be an Anki add-on that will use generative AI to rephrase the Anki cards in order to ask the question
in a slightly different way. This is done in order to avoid having the user associate the answer of the question to
the specific formulation of the question, rather than the semantic content of the question.

### Workflow

The add-on will replace the original note with the newly generated one. Once the user presses the button to show
answers, both the original and the generated notes will be shown.

### Technical Specifications

- The add-on will work only for regular and cloze deletion cards.
- The add-on will default to ChatGPT as the generative AI model.
- It must be developed with the idea to easily replace the generative AI model with another one.
- Ideally, it must prefetch the generated notes in order to avoid the user waiting for the note to be generated.
- It should also store the generated notes in main memory in order to operate smoothly on "undo" and "redo" operations.