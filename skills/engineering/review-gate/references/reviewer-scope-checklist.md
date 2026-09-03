# Reviewer Scope Checklist

This reference document defines the boundary and checklist for independent semantic review passes, shared by `review-gate` and `subagent-pipeline`.

## Mechanical vs. Semantic Division of Labor

- **Mechanical checks** (linting, formatting, conventional style, straightforward static analysis, and basic unit test execution) are owned by automated CI and Alibaba Code Review.
- **Semantic review** (business logic, edge cases, regressions, security, contracts, and test adequacy) is owned by the independent reviewer.
- The reviewer must read existing CI and Alibaba Code Review findings before starting and must not repeat resolved mechanical issues.

## Reviewer Checklist

1. **Spec & Acceptance Criteria**: Does the implementation satisfy all stated acceptance criteria and solve the core problem without scope creep?
2. **Business Logic & Edge Cases**: Are edge cases, null states, boundary conditions, empty inputs, and unusual state sequences properly handled?
3. **Regressions & Backwards Compatibility**: Could existing callers, database records, background jobs, or user workflows break? Are breaking schema or API changes explicit and justified?
4. **Security & Authorization**: Are access controls, permissions, input sanitization, query parameterization, and secrets properly handled?
5. **Integration Contracts**: Are API schemas, queue payloads, database schema migrations, and event signatures preserved across client/server and inter-service boundaries?
6. **Test Adequacy**: Are automated tests comprehensive, non-tautological, and testing real behavior rather than mocked internals?

## Blocker Severity Threshold

- **Blocking**: Correctness bugs, security vulnerabilities, data corruption risks, broken backwards compatibility without justification, and missing acceptance tests for stated criteria.
- **Non-blocking (apply if cheap)**: Concrete, self-contained improvements to clarity, safety, or documentation that do not require architectural churn.
- **Non-blocking (note only)**: Minor stylistic preferences, speculative "what if" suggestions, and subjective wording choices.
