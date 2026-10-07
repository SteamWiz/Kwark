# CHANGELOG

<!-- version list -->

## v3.0.0 (2026-10-07)

### Bug Fixes

- Avoid models.list() call when constructing AnthropicAIService
  ([#5](https://github.com/SteamWiz/Kwark/pull/5),
  [`6db9cf3`](https://github.com/SteamWiz/Kwark/commit/6db9cf350648c47fce8d66de571d38c5168485ce))

- Support models that reject forced tool use in kwark.ai.extract()
  ([#9](https://github.com/SteamWiz/Kwark/pull/9),
  [`06212fa`](https://github.com/SteamWiz/Kwark/commit/06212fa191b9df6b7b6f94afb129aa737a3e82f8))

- **ai**: Keep enum, const and pattern in extract() strict tool schema
  ([`cf702b3`](https://github.com/SteamWiz/Kwark/commit/cf702b38307cd2579a2bd54d9d6c6a3e27b461bb))

### Build System

- **deps**: Bump the actions group across 1 directory with 4 updates
  ([`da2abc6`](https://github.com/SteamWiz/Kwark/commit/da2abc6ec47d972e8ddae4858354078d0248b098))

### Features

- Add kwark extract command ([#10](https://github.com/SteamWiz/Kwark/pull/10),
  [`0d585a9`](https://github.com/SteamWiz/Kwark/commit/0d585a9fe02005ebc1a418dae793f1783ecc3b3c))

- Add kwark transcribe command ([#8](https://github.com/SteamWiz/Kwark/pull/8),
  [`1670fa2`](https://github.com/SteamWiz/Kwark/commit/1670fa226c72534edba419f39af45eb41943d2d6))

- Add kwark.ai library layer with transcribe() file-to-Markdown
  ([#7](https://github.com/SteamWiz/Kwark/pull/7),
  [`eb98116`](https://github.com/SteamWiz/Kwark/commit/eb98116aa300a68ab03f07e86067bd33c56de822))

- Add kwark.ai.extract() for JSON-schema structured output
  ([#9](https://github.com/SteamWiz/Kwark/pull/9),
  [`c4a8992`](https://github.com/SteamWiz/Kwark/commit/c4a899213d79f996da076074b82ea6189e90ea8f))

- Make mcp an optional extra (kwark[mcp]) ([#6](https://github.com/SteamWiz/Kwark/pull/6),
  [`2f588c8`](https://github.com/SteamWiz/Kwark/commit/2f588c8489dd6b5a78de81f201a1956eb5ea0378))

### Refactoring

- Share Anthropic client wrapper in kwark.ai; default extract() to Sonnet 5
  ([#9](https://github.com/SteamWiz/Kwark/pull/9),
  [`b6cd0ff`](https://github.com/SteamWiz/Kwark/commit/b6cd0ff89790ec560874335e0ec0f93865d3f312))

- Share one file-type table between kwark.ai and the activate command
  ([#7](https://github.com/SteamWiz/Kwark/pull/7),
  [`c3d255f`](https://github.com/SteamWiz/Kwark/commit/c3d255f25b7527e77836c61afe439f0a3e6dbe1c))


## v2.1.0 (2026-10-04)

### Bug Fixes

- Fail activate command on file upload error ([#1](https://github.com/SteamWiz/Kwark/pull/1),
  [`af588b5`](https://github.com/SteamWiz/Kwark/commit/af588b556cb46efb553f29d4c06688b5e106a83f))

### Continuous Integration

- Name the pull-request workflow 'PR Checks'
  ([`8833ac0`](https://github.com/SteamWiz/Kwark/commit/8833ac0387c628710c77af2270d1d9d5242d2d6e))

- Reference steamwiz/actions@v1
  ([`30b163d`](https://github.com/SteamWiz/Kwark/commit/30b163dddbacc2e765e89e5252d4711ea8f9ab45))

- Split PR checks from release; read-only PR token, one run per PR
  ([`7a06385`](https://github.com/SteamWiz/Kwark/commit/7a06385bb085b19ce2198c7603658c8c0cc75773))

### Features

- Default to Claude Sonnet 5 with thinking disabled ([#2](https://github.com/SteamWiz/Kwark/pull/2),
  [`d690d68`](https://github.com/SteamWiz/Kwark/commit/d690d68ffbb25817ecafb179e4950bc2578b98fc))


## v2.0.0 (2026-10-02)

### Build System

- **deps**: Drop unused requests, declare pyyaml (imported directly)
  ([`9125d1f`](https://github.com/SteamWiz/Kwark/commit/9125d1f12a31283cecbdb36074664e3f0436fe1c))

### Chores

- MIT license, copyright 2026 Francis Potter
  ([`5139a3f`](https://github.com/SteamWiz/Kwark/commit/5139a3fe707e9b6b025b84fc2a75f52b7177faa9))

- Remove GitLab reference from doc prompt
  ([`4a3f0fa`](https://github.com/SteamWiz/Kwark/commit/4a3f0fa76aaef35cf8c625a44495045889818500))


## v1.14.3 (2026-10-01)

- Initial Release
