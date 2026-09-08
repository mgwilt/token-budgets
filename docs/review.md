# Responding to a token finding

Token size is a review signal, not proof of architecture quality. A small file can
be poorly designed; a larger cohesive file can be justified. Review the changed
behavior and its callers before choosing a response.

- **Responsibilities:** Can you describe the file's purpose clearly? Are unrelated
  behaviors or policy decisions accumulating here?
- **Cohesive boundaries:** Would a module or document leaf have an independently
  useful purpose, or would the proposed split force readers to chase fragments?
- **Dependency direction:** Do implementation details depend on stable contracts?
  Would a split create cycles, hidden coupling, or unnecessary cross-module calls?
- **Interfaces:** Is the proposed boundary explicit and small? Are inputs, outputs,
  errors, ownership and lifecycle understandable to callers?
- **Tests:** Do behavior, failure paths, and boundary contracts remain covered?
  Do tests belong with the responsibility they verify?

For docs, use shallow discovery pages linked to independently useful leaves.
Before moving content, map every heading, source, link, caveat, criterion, example
and evidence item to a validated destination. Preserve original revisions and
stable references. Keep raw results and archives intact behind navigation.

Do not compress, minify, remove checks, types or evidence, or split mechanically
to meet a number. If a file remains cohesive, document a reviewed, narrowly scoped
threshold exception with a concrete reason. If boundaries improve, refactor with
relevant behavioral checks and update inbound links/callers. The utility proposes
review; it never edits files, stages fixes, or makes architectural judgments.
