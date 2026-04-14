# Guidelines for Using Tekton `when` Conditions

This document defines when pipeline-level `when` conditions can and cannot be used in this
project's Tekton pipelines. These rules exist because a skipped task still participates in the
pipeline graph: its results become empty strings, `runAfter` dependents still execute, and any
downstream task that consumes those empty results may silently misbehave or fail.

---

## Rules at a Glance

| Scenario                                                                                                                     | Allowed |
| ---------------------------------------------------------------------------------------------------------------------------- | ------- |
| Task has no downstream dependents                                                                                            | ✅ Yes   |
| `when` input is a pipeline parameter                                                                                         | ✅ Yes   |
| `when` input is a task result, the source task cannot be skipped, AND the guarded task has no task results in its own params | ✅ Yes   |
| `when` input is a task result AND the source task can itself be skipped                                                      | ❌ No    |
| `when` input is a task result AND the guarded task also consumes task results in its params                                  | ❌ No    |

---

## Rule 1 — No downstream dependents

A `when` condition is always safe when no other task depends on the guarded task's results or
uses it in a `runAfter` chain. There is no cascading effect if the task is skipped.

```yaml
# Safe: nothing downstream reads this task's results
- name: notify-slack
  taskRef:
    name: send-slack-notification
  when:
    - input: $(tasks.check.results.failed)
      operator: in
      values: ["true"]
  params:
    - name: message
      value: "Pipeline failed"
```

---

## Rule 2 — `when` input is a pipeline parameter

Using a pipeline parameter as the `when` condition input is always safe. Pipeline parameters are
resolved before any task runs and are guaranteed to be non-empty (or have a known default). No
task result propagation is involved.

```yaml
# Safe: condition is a pipeline param, not a task result
- name: publish-pyxis-data
  taskRef:
    name: publish-pyxis-data
  when:
    - input: $(params.cert_project_required)
      operator: in
      values: ["true"]
  params:
    - name: cert_project_id
      value: $(params.cert_project_id)
```

---

## Rule 3 — `when` input is a task result, source task cannot be skipped, guarded task has no task results in params

A task result can be used as a `when` condition input when **all three** of the following hold:

1. The task that produces the result **cannot itself be skipped** — it has no `when` condition and
   always runs. If the source task can be skipped, its result becomes an empty string, making the
   `when` condition unreliable (it may silently evaluate as if the condition were false, with no
   indication that the source task was skipped rather than producing a genuine empty value).
2. The guarded task's own params **contain no task results** — all param values come from pipeline
   parameters, literal strings, or workspace references.
3. Downstream tasks that receive the guarded task's results must already handle empty values (via
   their own `when` conditions or inner script guards), since a skipped task's results become empty
   strings.

```yaml
# NOT allowed: source task (some-upstream-task) has its own when condition and can be skipped.
# If it is skipped, its result is "", and the when condition below becomes meaningless.
- name: some-upstream-task
  when:
    - input: $(params.flag)
      operator: in
      values: ["true"]
  ...

- name: guarded-task
  when:
    - input: $(tasks.some-upstream-task.results.value)  # ❌ source can be skipped
      operator: notin
      values: [""]
  ...
```

```yaml
# Safe: when uses a task result, source task always runs (no when condition), guarded task
# params are all pipeline params
- name: link-pull-request-with-open-status
  taskRef:
    name: link-pull-request
  when:
    - input: $(tasks.get-ci-results.results.test_result_id)  # get-ci-results always runs ✓
      operator: notin
      values: [""]
  params:
    - name: pipeline_image
      value: $(params.pipeline_image)   # pipeline param — OK
    - name: pyxis_url
      value: $(params.pyxis_url)        # pipeline param — OK
```

---

## Rule 4 — `when` input is a task result, guarded task also consumes task results in params ❌

This combination is **not allowed**. When the `when` condition is based on a task result and the
guarded task also consumes task results in its own params, skipping the task creates an ambiguous
state in the result propagation chain:

1. The upstream tasks that produced the param results ran and completed.
2. The guarded task is skipped — those results are not consumed and not transformed.
3. Any downstream task expecting the guarded task's output receives empty strings, with no clear
   signal about whether the skip was intentional.

This makes the pipeline hard to reason about and can cause silent failures downstream.

```yaml
# NOT allowed: when uses a task result, AND params also reference task results
- name: get-pyxis-certification-data
  taskRef:
    name: get-pyxis-certification-data
  when:
    - input: $(tasks.certification-project-check.results.certification_project_id)  # task result
      operator: notin
      values: [""]
  params:
    - name: cert_project_id
      value: $(tasks.certification-project-check.results.certification_project_id)  # also task result ❌
    - name: pyxis_url
      value: $(tasks.set-env.results.pyxis_url)                                     # also task result ❌
```

**How to fix this:** instead, add an inner guard in the task script and rely on the task's own
early-exit logic to handle the empty-input case, as was the established workaround pattern in
this project.

```bash
# In the task script — guard against empty cert_project_id at the script level
if [ "$(params.cert_project_id)" == "" ]; then
  echo -n | tee "$(results.foo.path)"
  exit 0
fi
```

---

## Summary Decision Tree

```
Is the task being considered for a when condition?
│
├── Does it have no downstream dependents?
│   └── YES → ✅ Use when condition freely
│
├── Is the when condition input a pipeline parameter?
│   └── YES → ✅ Use when condition freely
│
└── Is the when condition input a task result?
    │
    ├── Can the source task itself be skipped (does it have a when condition)?
    │   └── YES → ❌ Do NOT use when condition
    │               Use an inner script guard (exit 0) instead
    │
    └── Does the guarded task's params contain any task results?
        ├── NO  → ✅ Use when condition (self-contained skip)
        └── YES → ❌ Do NOT use when condition
                    Use an inner script guard (exit 0) instead
```

---
