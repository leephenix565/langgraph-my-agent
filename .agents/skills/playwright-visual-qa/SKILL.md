# playwright-visual-qa

## Use When

- Running visual QA or browser smoke checks for `apps/web`
- Capturing screenshots for the chat shell, workflow expansion states, or agent catalog views

## Boundaries

- Focus on visible UI behavior, not runtime integration semantics.
- Do not treat browser automation as a substitute for public-contract review.
- Keep screenshots and assertions aligned with the single-assistant transcript model.

## Expected Outputs

- Repeatable smoke or visual checks for the frontend shell
- Screenshots or test evidence for desktop workflow states when requested
- Clear notes on whether the run used mock fixtures or live data
