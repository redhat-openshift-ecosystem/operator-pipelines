## ci.yaml config
Each operator submitted as a certified or marketplace operator needs to contains
a `ci.yaml` config file that is used during the certification.

The correct location of this file is at `operators/operator-XYZ/ci.yaml` and
needs to contains at least following values:

```yaml
---
# The ID of certification component as stated in Red Hat Connect
cert_project_id: <certification project id>

```

Other optional value is `merge: false` that prevents from automatically merging
a pull request with an operator if all tests passes. The default behavior is to
merge a PR automatically.