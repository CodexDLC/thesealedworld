# Battle-Simulation Training for Combat AI

Status: idea for future combat-AI work.

The current offline trainer (`src/backend/features/combat/runtime/ai/training`)
uses `ScoringEnvironment` — a fast tag-matching reward over ~29 synthetic
`SyntheticScenario` fixtures. Every reward is "did the brain pick a feint
whose semantic tags overlap the labelled expected_tags". It does not run the
real `CombatPipeline`.

A real battle simulator already exists (`InMemoryCombatSimulator` +
`AiSimulationIntentProvider`) and a `BattleTrainingEnvironment` skeleton sits
in `runtime/ai/training/battle_environment.py`. They are not wired into the
trainer: `train_policy.train()` still imports `ScoringEnvironment` only, and
no battle scenarios are catalogued.

This doc captures the plan for that wire-up and the next-step neural extension.

## Current state

- `InMemoryCombatSimulator.run(state)` — gives `SimulationRunResult` with
  winner, rounds, per-actor final HP, and a `CombatTelemetry` snapshot
  (damage, healing, deaths, control, buffs, resources, failed actions).
- `BattleTrainingEnvironment.evaluate(policy)` — async, takes a list of
  `BattleSimulationScenario(state_factory, expected_winner)`, runs the
  simulator once per scenario, derives a reward from telemetry + winner.
- `evolve()` and `train()` are sync and only know about `ScoringEnvironment`.
- No battle-scenario catalogue exists yet.

## Open questions to settle before coding

1. **Hybrid or replacement?** Tag scoring is fast, dense, interpretable.
   Battle reward is realistic but slow and noisy. The pragmatic choice is a
   hybrid: tag-matching as the dense backbone, battle as a slower but
   ground-truth signal.
2. **Reward variance.** A single battle is stochastic. Without replay
   averaging the trainer chases noise. Options:
   - replays=3 with swept `(policy_id, scenario_name, replay_idx)` seeds and
     mean reward;
   - or fixed deterministic seed per `(policy, scenario)` so a single run
     is reproducible (cheaper but the trainer can find a seed-specific
     exploit).
3. **Simulator determinism under a fixed seed.** Must be verified first.
   `MathCore.random_range`, `roll_chance`, and any other entropy source must
   accept a seeded RNG, otherwise replay averaging buys nothing.
4. **Sync vs async.** `evolve()` is sync; `BattleTrainingEnvironment.evaluate`
   is async. Either wrap with `asyncio.run` inside `evolve`, or rewrite
   `evolve` as async. Wrapping is the smaller delta.

## Time budget

| Variant | One evaluation | 20×10 run | Notes |
|---------|----------------|-----------|-------|
| Tag only (today) | ~30 µs × 29 scen = ~1 ms | seconds | Fast, dense, ignores resolver realities. |
| Battle, replays=1 | ~50 ms × 8 scen = ~400 ms | ~80 sec/gen | One bad seed dominates. |
| Battle, replays=3 | ~150 ms × 8 scen = ~1.2 s | ~4 min/gen | Reasonable variance. |
| Hybrid (29 tag + 5 battle × 3) | ~750 ms | ~2.5 min/gen | Overnight-friendly. |

Numbers are pessimistic — they assume one full battle takes ~50 ms in Python.
Profile before committing.

## Canonical battle scenarios (first cut)

Each is a `BattleSimulationScenario(name, state_factory, expected_winner=None)`
built via `runtime/simulation/factory.py` or the equivalent in-memory state
builder. Single state, fixed actor snapshots, no Redis.

| Name | Setup | Axis under test |
|------|-------|-----------------|
| `duel_sword_vs_sword` | 1v1, equal stats, sword vs sword | Baseline competence, terminates in finite rounds. |
| `duel_armor_vs_archery` | Heavy armor vs archer | Reward for picking armor-bypass feints. |
| `duel_shield_vs_macer` | Shield+block vs ignore-block macer | Reward for picking anti_block. |
| `duel_wounded_vs_fresh` | Bot at low HP vs fresh enemy | Reward for healing/defensive prep over attack. |
| `swarm_2v3` | 2 PCs vs 3 mobs | Reward for multi_target / team_focus axes. |
| `prep_dispel_required` | Enemy carries `prep_counter_on_dodge` | Reward for dispel over attacking through prep. |

This set covers exactly the axes that the PR6 tag scenarios already label, so
the two signals can be checked for agreement during a hybrid run.

## Minimal wire-up steps

Each step is an isolated 50-150 line change with its own test.

1. **Determinism guard.** Test that two runs of the same simulator state
   with the same seed produce identical winner + final HP + telemetry. If it
   fails, fix `MathCore`/`roll_chance`/etc. to accept a seeded RNG threaded
   through `BattleContext`.
2. **Catalogue.** New
   `src/backend/features/combat/runtime/ai/training/battle_scenarios.py`
   exporting `default_battle_scenario_set() -> list[BattleSimulationScenario]`
   with the six fixtures above.
3. **Replay averaging.** Extend
   `BattleTrainingEnvironment.evaluate(policy, replays=3)` to sweep seeds
   per `(policy, scenario, replay_idx)` and average.
4. **Hybrid environment.** New
   `runtime/ai/training/hybrid_environment.py`:
   `HybridEnvironment(tag_env, battle_env, alpha=1.0, beta=5.0)` calling
   both and returning `α·tag_total + β·battle_total`. Run mode is async to
   match `BattleTrainingEnvironment`.
5. **Trainer CLI flag.** `TrainArgs.env_mode: Literal["tag","battle","hybrid"]`
   default `"tag"` (regression-safe). `--env-mode` CLI flag.
6. **Smoke + comparison test.** `pytest` smoke that `train(env_mode="hybrid")`
   writes the same artefact shape and that battle reward of the trained
   policy beats a `Policy.with_defaults()` baseline on the same scenario set.

## What NOT to do in this MVP

- **REINFORCE / policy gradient.** Requires rewriting `brain.decide_turn` on
  softmax sampling + log_prob trace through the battle. Different track.
- **Hidden-layer policy.** Today's reward signal is barely dense enough for
  the 41 existing linear weights. Adding hidden layers without first
  enlarging the corpus would just overfit. Track separately (see below).
- **Self-play.** Two brains vs each other. Brings mode collapse and
  exploitation cycles — needs tournament selection or a league system.
  Worth doing after the catalogue is mature.
- **Per-population parallelism.** `asyncio.gather` reads attractive but the
  simulator is single-threaded today. Real speedup needs process pools.
  Defer.

## Possible extension: minimal 2-layer policy

When the reward signal becomes dense enough (≈100+ scenarios + battle
reward), a natural next step is replacing the linear scorer with a one-hidden-layer
MLP. Today's scorer is mathematically `nn.Linear(in=~41, out=1, bias=False)`
— a single perceptron over hand-crafted semantic tags. The minimal
upgrade is:

```
features (≈41) → Linear(41, 24) → ReLU → Linear(24, 1) → score
≈ 41×24 + 24 + 24×1 + 1 = 1 009 parameters
```

Properties of that upgrade:

- **Inference cost.** Per-action scoring grows from ~5 µs to ~20–40 µs in
  Python; still well below the Redis/pipeline overhead per turn.
- **Storage.** `policy.json` grows from ~2 KB to ~8–12 KB. `PolicyStore`
  contract is unchanged; only the weight payload schema gets an extra layer.
- **Training.** Evolution still works at ~1 000 params with `population≥50`
  but gets slow. The cleaner path is REINFORCE / vanilla policy gradient
  with the battle environment supplying the reward — `~50` more lines of
  code on top of this MVP.
- **Cabinet.** Already covered by `CombatAiConfig.ACTIVE_POLICY_ID`. Admin
  swaps between linear and MLP policies by changing one Redis key — no
  code path forks.

What this unlocks vs the linear scorer:

- Nonlinear feature interactions, e.g. "pick AoE only if swarm HP is below
  overkill threshold **AND** stamina supports a second swing".
- Per-weapon-class specialisation without separate policies — one small
  hidden layer can route by the existing `group_weapon` tag.
- A real gradient signal across the full feature space, where today
  ~30 weights stay near zero because no scenario provides a label for them.

The upgrade is mostly a refactor of `Policy.weights` from
`dict[str, float]` to a structured payload with named layers, plus a small
`policy.evaluate_features(...)` switch from dot product to two-layer forward
pass. Not a research project — a follow-up implementation task once the
battle environment has been wired and the corpus has grown.

## Pitfalls to watch

- **Telemetry sensitivity.** The current `_score_result` uses arbitrary
  coefficients (`0.02 * damage`, `0.5 * deaths`, etc.). The trainer will
  happily exploit any miscalibration. Re-tune them after the first hybrid
  run and codify the ratios as cabinet-tunable knobs under `combat_ai` if
  they need frequent adjustment.
- **Action provider coupling.** `AiSimulationIntentProvider` constructs a
  fresh `MonsterCombatBrain(policy)` per simulator. Make sure the trainer
  passes the same `policy` instance throughout one evaluation; mixing
  policies inside one battle is silent and will look like noise.
- **Scenario brittleness.** If a fixture relies on a specific feint id in
  the bot's hand and the catalog renames it, the run silently degenerates.
  Mirror the
  `test_pr6_expected_feints_resolve_to_real_catalog_entries`-style guard
  from `test_ai_training.py` for the new battle catalogue.
