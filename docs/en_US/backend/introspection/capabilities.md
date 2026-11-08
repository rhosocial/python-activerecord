# Capability Probes

The introspection described in [Database Introspection](../introspection.md) is a
set of questions addressed to a database, and not every database answers every
one of them. Asking a question a server cannot answer costs more than a failed
call: it costs the caller the branch it wrote for that answer, and it costs the
reader the difference between "nothing to report" and "no way to report". Each
family therefore has a probe on the dialect, a `supports_*` method returning a
bool, and a caller consults it before spending anything.

This page documents what those probes promise. It does not document what any
particular connection answers.

## Why a Probe Exists

A caller that wants a report of unused indexes has two questions, not one: can
this server answer, and what does the answer cost. The second is the business of
the method's own docstring. The first is the probe's, and it exists so that the
caller can decide before paying rather than after failing.

The answer has to be a fact about the server currently connected to, not a guess
about the product it belongs to. A dialect is therefore adapted to the server
before the probe is consulted: `backend.introspect_and_adapt()` reads the
version, settles the capabilities that depend on it, and only then is the
question worth asking. A dialect that has not been adapted can still answer what
it knows without a handshake, and `version_at_least()` is the predicate such a
check must use -- it never raises, and it answers `False` when no version has
been confirmed, because a capability nobody has confirmed is not claimed.

### An Answer About the Server, Not the Library

A probe is not a static feature flag on the dialect class. A capability gated on
`version_at_least((3, 0, 0))` answers one way against one server and another
against a different version of the same product; that is the intended behaviour,
because the probe is evaluated for the connection in hand. Caching an answer on
the class would make a report written against one server describe a different
one.

## What True Promises

`True` means this engine will answer. It does not mean the answer has this shape,
or that the answer is cheap, or that every field a result type declares will be
populated. A probe answers one question -- whether a question can be asked --
and the rest is carried by the method, its result type and its docstring.

### It Does Not Promise a Shape

Every `True` carries an obligation. `supports_runtime_stats()` obliges
`format_runtime_metrics_query_statement()` to render for this dialect;
`supports_unused_indexes_detection()` obliges
`format_unused_indexes_query_statement()`; and so on across the family. A
promise with no formatter behind it is not a capability, it is a claim that the
next call will refuse.

What the rendered query returns is narrower than the probe: at minimum the
address columns the result type can carry, with each family's own contract stated
where its formatter is documented. The probe never promises fields, only
availability.

### False Means Do Not Ask

`False` is a complete answer rather than a failure. The caller learns that no
attempt is worth making and takes its fallback knowingly. A backend that cannot
answer must answer `False` and say why in the probe's docstring -- what the
question would have needed, and why the material is not there. The docstring is
the evidence for the claim, and a `False` with no reason written beside it is a
claim the next reader has to take on faith.

`False` is also not an empty result. An empty list says the question was asked
and the answer is nothing; `False` says the question was never asked. A caller
that conflates them will report "no unused indexes" for a server that keeps no
counter, which is the one report an operator must not receive.

### An Unanswered Slot Is Not an Unanswered Capability

Inside an answer, absence and refusal are separate facts. A slot that is `None`
means the server answered and did not measure that field -- an untracked counter,
a figure the engine does not keep. A probe that is `False` means no answer was
produced at all. Reading the first as the second throws away measurements that
were taken; reading the second as the first invents an answer nobody produced.
The probe is the only place the two can be told apart before the call, which is
why it is checked first.

### Two Broken Promises

The rule that a probe must neither overclaim nor underclaim exists because both
failures are quiet at the call site.

Overclaiming is a `True` with no formatter behind it. The caller is told yes,
commits to the report path, calls the method and is refused:
`UnsupportedFeatureError` when the dialect declares no formatter at all,
`ProtocolNotImplementedError` when what answered the lookup was the protocol stub
rather than a formatter. The exception is not the damage. The damage is that the
caller has already written and tested a branch it cannot use, and code that
catches the refusal will silently prefer a fallback it never needed. A probe
left `True` with nothing behind it is a broken promise.

Underclaiming is a `False` that should have been `True`. Nothing raises, nothing
is logged, and no caller learns that the question was answerable. The capability
is not merely missing; it is invisible, and every consumer takes the fallback
forever. Overclaiming is noticed at the first call, while underclaiming is
noticed by nobody -- which is why the second half of the rule matters more than
it looks.

## How to Use One

Check the probe, then call the method. That is the whole convention, and it is
worth writing out because no return type enforces it.

```python
unused = []
if backend.dialect.supports_unused_indexes_detection():
    unused = backend.introspector.list_unused_indexes()

for row in unused:
    print(row.schema, row.table_name, row.index_name)
```

An empty `unused` here is a legal answer from a server that can answer: no index
in the current window is unused. It is not the same fact as the probe answering
`False`, and the probe is what keeps the two apart at the call site.

### The Probe Decides Whether; the Docstring Decides What It Costs

The cost of a family is stated in the public method's own docstring, not in the
probe. `True` says the question can be answered; it does not say the answer is
cheap, and treating the probe as a cost estimate would make the expensive
families look free. A caller that needs the price reads the method it is about
to call.

Probes are dialect methods rather than calls on the introspector, so they are the
same on the async introspector as on the sync one; only the call itself is
awaited under the same name.

```python
async def table_report(backend):
    if not backend.dialect.supports_table_stats():
        return []
    return await backend.introspector.list_table_usage_stats()
```

## Discovering the Full Set

Probes are declared on the dialect rather than collected in a registry, so the
set is readable from the objects themselves. The protocol declares all of them,
which is what makes introspection of introspection possible without reading
source: ask the protocol for its `supports_` names, then ask the adapted dialect
each one.

```python
from rhosocial.activerecord.backend.dialect.protocols.introspect.introspection import (
    IntrospectionSupport,
)

probe_names = sorted(
    name for name in dir(IntrospectionSupport) if name.startswith("supports_")
)
answers = {name: getattr(backend.dialect, name)() for name in probe_names}

for name in probe_names:
    print(f"{name}: {answers[name]}")
```

The loop returns declarations, not measurements: what it lists is the questions
this dialect claims to answer. Whether a claim is kept is a different test --
calling the method -- so the loop is a starting point for a support report, not
a certificate for one.

> Which probes answer `True` differs by backend; each backend's documentation
> states its own.
