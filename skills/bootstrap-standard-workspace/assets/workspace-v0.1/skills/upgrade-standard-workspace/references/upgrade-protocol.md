# Upgrade Protocol

## Release manifest

The preview script uses a JSON manifest:

```json
{
  "schema_version": "0.1",
  "release_version": "0.2.0",
  "files": [
    {
      "path": "skills/example/SKILL.md",
      "owner": "distribution",
      "sha256": "64-character-lowercase-hex"
    }
  ]
}
```

This JSON is the integrity manifest used by an immutable stable Release and its installed receipt. It is fixed at `.ai-workspace/release-manifest.json` and contains the schema version, release version, ownership, and file hashes. It is not `.ai-workspace/distribution.manifest`: the latter is only a plain-path allowlist used by Doctor and repair flows to compare distribution paths and ownership. It must not be passed to the upgrade preview or converted into a Release manifest with hashes calculated from the current workspace.

- `schema_version` is `0.1`; only `schema_version`, `release_version`, and `files` are allowed at the top level.
- `path` is a workspace-relative file path with no `..`.
- `owner` is one of `distribution`, `generated`, or `workspace`.
- Every path appears exactly once.
- `files` corresponds exactly to every regular file in the release asset except `.ai-workspace/release-manifest.json` itself.
- Every candidate file matches its `sha256`.
- Current-manifest hashes determine whether release files were modified locally; do not recalculate them from current files and overwrite the record.

The manifest does not hash itself, avoiding a recursive digest. Trusted candidate-receipt bytes are protected by the Bootstrap Skill's outer `checksums/workspace-v0.1.sha256` and, in the future, an optional Release signature. Validate the outer protection before preview. The preview also confirms that `--current-manifest` is byte-identical to the installed receipt, `--candidate-manifest` is byte-identical to the candidate directory receipt, and no unlisted file exists in the candidate directory.

## Ownership handling

| Owner | Upgrade action |
|---|---|
| `distribution` | Add, replace, or remove only when the current file still matches the installed Release hash; local modification is a conflict. |
| `generated` | Recompile from new structured facts and policies; candidate files are only compiler input or validation fixtures. |
| `workspace` | Always preserve; new-version content is an optional seed accepted only by user choice. |

An explicit Migration explains every ownership change and lists it separately for confirmation. Without a Migration, ownership change remains a conflict.

## Preview actions

- `add`: add a release file where the target path does not exist.
- `replace`: replace an unmodified current release file when candidate content changed.
- `remove`: remove an unmodified old release file omitted by the candidate manifest.
- `unchanged`: current and candidate hashes are identical.
- `preserve`: preserve a workspace file.
- `offer-seed`: offer a new workspace template when the target is absent, without writing automatically.
- `regenerate`: regenerate from sources of truth after upgrade.
- `replace-receipt`: atomically replace the installed receipt after all other actions and validation succeed; never execute earlier.
- `conflict`: local modification, unknown path occupant, ownership change, missing file, or hash mismatch.

When any `conflict` appears, `safe_to_apply` must be `false`.

## Snapshot requirements

A snapshot covers at least:

- identity, version, manifests, state, and upgrade transaction data under `.ai-workspace`;
- every existing file planned for addition, replacement, removal, or regeneration;
- unknown and untracked user files in affected parent directories;
- all `workspace` metadata changed by a Migration, including `locales/` content when affected;
- current release pointers or installation-directory links.

A Git commit alone does not protect untracked files, nested repositories, external symlink targets, and workspace data outside Git. A VCS snapshot must supplement these items.

The snapshot receipt records time, workspace, current version, file list, hashes, location, and restore command. Stop the upgrade when the restore path cannot be verified.

## Confirmation content

Before applying, ask the user to confirm all of these facts:

1. current version and target immutable Release;
2. Migration chain and irreversible steps;
3. action counts and per-conflict decisions;
4. protection outcome for `workspace` content;
5. snapshot receipt and rollback command;
6. whether download, network, deletion, symlink switching, or external-process restart is required;
7. post-upgrade validation and failure handling.

A plan change, candidate-content change, or snapshot failure invalidates earlier confirmation and requires a new preview and confirmation.

## Commit the installed receipt

`.ai-workspace/release-manifest.json` does not participate in `files` as an ordinary `distribution` file. The preview represents it separately as `replace-receipt`. During application:

1. keep the old receipt unchanged while completing all other file actions, Migrations, generation, and validation;
2. update version locks and release pointers;
3. verify again that candidate-receipt bytes match the authenticated candidate Release;
4. atomically replace the receipt as the transaction's final workspace write;
5. on failure, fail and roll back rather than leaving a mixed "new version, old receipt" state.

After successful receipt replacement, do not run generation, formatting, migration, or repair that writes to the workspace.

## Self-update

V0.1 defines the protocol only. Before a canonical formal repository, stable tag, immutable Release, complete verification, and trusted switch mechanism exist:

- version checks require authorization;
- downloads to a sibling directory require authorization;
- automatic application is prohibited by default;
- an executing Skill must not overwrite itself;
- the latest branch commit must not substitute for a Release.
