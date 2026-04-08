# frontend-shell-deerflow

## Use When

- Building or revising `apps/web`
- Shaping the chat-first shell, sidebar, composer, answer card, or workflow inspector
- Adjusting mock transcript or workflow fixtures for the public UI

## Boundaries

- Keep one assistant persona in the chat transcript.
- Keep workflow as a summarized process layer, not as multi-speaker chat.
- Do not connect the shell directly to LangGraph runtime in Phase F1.
- Do not render raw graph messages, raw prompts, raw assignments, or raw agent JSON.

## Expected Outputs

- A chat-first UI with safe public transcript semantics
- A collapsed-by-default workflow panel
- Mock fixtures that can later map onto a public adapter without changing the visible contract
