# Execution Sequence

## `default_fallback_profile` sequence
1. system_analyst
2. requirements_reviewer
3. human_engineer (`REQ_FREEZE_APPROVAL`)
4. architect
5. architecture_reviewer
6. devops_engineer
7. backend_engineer
8. frontend_engineer
9. implementation_reviewer
10. qa_engineer
11. security_engineer
12. ai_evaluator
13. sre_engineer
14. technical_writer
15. release_reviewer
16. release_manager
17. human_engineer (`RELEASE_APPROVAL`)

## Notes
- Runtime sequence is sourced from profile YAML, not this file.
- Reviewer `changes_requested` reroutes to producer role.
