# Workflow Exceptions

Some parts of the pipeline can be changed using approved exceptions.
The exceptions respect GitHub labels and repository configuration similarly
to static and dynamic checks.

Only repository maintainers are able to set exceptions for operators. Contact
the repository maintainers if you need an exception for your operator.

## Repository Configuration

The configuration takes place in `config.yaml` file in the root of the operator
repository. There, a top-level key `allowed_exceptions` handles the
configuration. The value of this key is expected to be a mapping of an
exception name mapped to a list of regular expressions for operators
that have the given exception.

## Labels

The exception are also applicable with GitHub labels. The label name searched
for is always in this format: `exception/<exception_name>`.

## Possible exceptions

### `duplicate_name`

This exception allows operators to have the same name in different operator
sources. When checking and reserving ISV operator name, this exception allows
operators in different source catalogs (Marketplace, Certified) share the same
name. Operators still must have a unique name within each source even with
this exception applied.

## Example configuration

```yaml
...
allowed_exceptions:
  duplicate_name:
    - '^operator_foo'
...
```
