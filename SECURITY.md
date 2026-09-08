# Security

For a security-sensitive report, open an issue requesting a private reporting
channel without publishing exploit details or affected source content. Wait for
a maintainer to arrange that channel before sharing a sensitive reproduction.
Do not include credentials, proprietary files or personal data in public issues.

The utility counts source locally and does not execute it. Initial dependency and
encoding setup may access the network and write caches. JSON reports omit source
excerpts, but repository paths, counts and hashes can still reveal information;
review reports before sharing them.

Policies and the checker itself are trusted configuration. Local Git hooks are
developer checks, not a security boundary. Review checker revisions and policy
exceptions before using them in a repository or build system. See
[checks and integration](docs/checks.md) for the exact read-only contract.
