This is an add-on for the spaced-repetition flashcard app [Anki](https://apps.ankiweb.net/).
It uses ChatGPT to rephrase the card question at time of review in order to force the user to focus on the
question semantics rather than to memorize and respond to the exact wording of the question.

<p style="text-align:center"><img src="resources/ml-tutor-basic.png" width="700"><br><img src="resources/ml-tutor-cloze.png" width="700"></p>

### Motivation

Human memory is highly visual. I find myself often responding to the particular visual organization of an Anki question
rather than the actual meaning of the question. In addition, the more different variations/conditions under which we
recall a topic, the more generalized that memory becomes. This add-on aims to help with both of these issues.

### The Add-on

This add-on uses OpenAI's ChatGPT to rephrase the question at the time of review. As such, it requires an internet
connection and a valid API key (see [here](https://platform.openai.com/docs/quickstart/account-setup) for more
information).

The add-on operates exclusively on the HTML text before it is displayed by Anki. As such, it never modifies the notes
themselves. Notes are rephrased slightly ahead of time in order to provide a smoother experience, but if the user
goes through the notes quickly, there may be some loading time before a subsequent note is rephrased.

Rephrased notes are cached for the duration of the app session, meaning that the same rephrasing will be reused
until the app is restarted, at which point a new phrasing will be generated. Editing a note will trigger a new
rephrasing.

The formatting of the answer is preserved, but the rephrased question does not attempt to mimic the formatting of the
original question in any way. In other words, the rephrased question is in plain text.

### Supported Note Types

- basic
- basic (and reversed card)
- cloze

### Installation

- Install the add-on from AnkiWeb [here](https://ankiweb.net/shared/info/1505658371).

### Configuration

In the configs (Tools -> Add-ons -> select "ML-Tutor" -> Config), you can set the API key, the OpenAI model
(see [OpenAI models](https://platform.openai.com/docs/models/models)), and whether the original question of the
note should be displayed along with the answer. The configuration changes do not require a restart of the Anki app.

#### A Note On GPT Models

GPT-4 models are currently only available to [paying customers](https://help.openai.com/en/articles/7102672-how-can-i-access-gpt-4),
which means that you need to pay a monthly bill of at least 5 USD before you can use those models. GPT-3 are available
to everyone (but still on a pay-per-use basis).

### Contributing

- Pull requests to the [repo](https://github.com/petioptrv/ml-tutor) are welcome!
- For bugs/issues and feature requests, please open an [issue ticket](https://github.com/petioptrv/ml-tutor/issues).
  - The more information you provide, the better. For example, if you are experiencing a bug, please provide the
    following:
    - The note type of the card
    - The card's HTML
    - The error message
    - The expected behavior
    - The actual behavior
    - The steps to reproduce the error
    - Screenshots

### Contact

petioptrv@icloud.com