This is not a task for `wizard`. Renaming `@acme/widgets` to `@acme/gizmos` in
`package.json` and updating the matching imports does not require a human to
click through a third-party dashboard, enter a credential, or perform any
step the agent cannot do itself — the agent can perform this rename and every
import update directly. No wizard needed; making the edits directly and
running the test suite is the right approach here, not a wizard script.
