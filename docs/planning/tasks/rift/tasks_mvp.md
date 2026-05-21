# Rift MVP Tasks

The MVP proves personal quest rifts. It should not implement anchor rifts, territory, outposts, portal circles, public outbreaks, or raid content.

## Phase 0: Design Lock

- [ ] Confirm first contract board shape: 5-6 notices with tier, setting/risk/reward, distance, task type.
- [ ] Confirm which contract types ship first: close core, kill family, retrieve item, gather/resource task, or a smaller subset.
- [ ] Confirm whether first MVP supports solo only or solo plus party.
- [ ] Confirm death behavior for tier 1 and tier 2 rifts.
- [ ] Confirm initial core handling actions.

Needs owner decision:

- Whether personal rifts allow party entry in the first playable slice.
- Whether dirty loot loss is active from tier 1 or introduced after tutorial tier.

## Phase 1: Contract Board

- [ ] Create a gameplay contract-board concept for the adventurers guild.
- [ ] Generate 5-6 notices for the active character.
- [ ] Include weaker, equal, and harder options relative to the character's current readiness.
- [ ] Each notice must expose enough info for a quick choice.
- [ ] Accepting a notice creates/selects a rift target and entrance location.

Acceptance:

- The player can open a board and see multiple rift-related choices.
- Each choice has a clear risk/reward identity.
- Accepting one creates a concrete target state.

## Phase 2: Travel To Entrance

- [ ] Create or reuse world/exploration flow for travelling to the rift entrance.
- [ ] Select entrance region by rift tier.
- [ ] Allow travel encounters before the rift.
- [ ] Support rift-linked monster-family ambushes near the destination.

Acceptance:

- A contract does not teleport directly into the rift by default.
- The route can produce events and danger.
- Portal shortcuts can be added later without changing the core loop.

## Phase 3: Rift Run

- [ ] Create a personal rift instance from a generated or reused template.
- [ ] Generate a small graph of nodes.
- [ ] Track current node, discovered nodes, core state, and run status.
- [ ] Resolve movement between graph nodes.
- [ ] Place combat encounters using encounter budget.
- [ ] Place the rift core.

Acceptance:

- A player can enter, move through nodes, fight, and reach a core.

## Phase 4: Rewards And Core

- [ ] Grant symbiote experience from rift monsters.
- [ ] Grant rift substances/materials from monsters.
- [ ] Add dirty-loot status to rift rewards.
- [ ] Add initial core action: break or absorb.
- [ ] Add extraction-skill hook even if exact skill math is temporary.

Acceptance:

- Completing a rift gives meaningful rift rewards.
- Rewards are visibly dirty until synced.
- Core resolution ends the personal rift.

## Phase 5: Verification

- [ ] Add focused tests for contract generation.
- [ ] Add focused tests for rift instance lifecycle.
- [ ] Add focused tests for encounter budget conversion.
- [ ] Add focused tests for dirty-loot sync/loss behavior.
- [ ] Add frontend contract tests for the rift screen.

Needs owner decision:

- Exact MVP quality gate can be selected after files are known.
