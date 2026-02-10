# Context Plugin Contract

## Intent ingestion model
1. Human engineer/client starts a new idea or task by default.
2. Bot/GPT can assist by clarifying and recommending priority.
3. Human approval is required to activate an idea for execution.
4. Activated context must bind to a chosen workflow profile.

## Required context fields
Context frontmatter must include:
- `idea_id`
- `headline`
- `owner`
- `profile`
- `created_at`
- `status`

## Activation handshake
1. Bot drafts structured context from chat.
2. Human confirms or edits draft.
3. System records activation event and selected profile.
4. Orchestrator loads `active_profile` from context and status.

## Governance note
Bot recommendations never override human decision authority.
