# Flow v1

## Goals

- Keep assets readable and versionable.
- Share business intent across desktop, Android and iOS.
- Keep selectors declarative and fallback order explicit.
- Allow multiple assertions after one action.
- Make failure handling and continuation visible in the asset.

## Selector policy

Prefer stable semantic selectors in this order when available:

1. test identifier
2. accessibility identifier or role
3. stable text
4. DOM CSS/XPath
5. OCR
6. image template

The runner does not invent fallback selectors. Authors or an AI-assisted review must persist alternatives before execution. This keeps regression deterministic and auditable.

## Compatibility

`schema_version` changes only for breaking changes. Additive fields remain optional. Migrators will transform older assets before validation; drivers receive only the normalized in-memory model.

