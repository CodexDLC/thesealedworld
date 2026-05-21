# Weapon Type Source

Status: design and catalog-expansion source. Item ids and trigger ids must be
verified against the current item and combat catalogs before implementation.

This document preserves useful weapon-type direction from the old RPG rules. It
is not a complete item catalog and not runtime truth.

## Weapon Groups

Weapon groups should align with current skill ids:

| Weapon group | Skill key | Design direction |
| --- | --- | --- |
| Swords | `skill_swords` | Balanced weapon mastery, bleeding, reliable crits, parry-friendly blades. |
| Macing | `skill_macing` | Impact, armor pressure, stun, heavy strike, shield pressure. |
| Archery | `skill_archery` | Distance, high impact shots, piercing, evasive rhythm. |
| Polearms | `skill_polearms` | Reach, distance control, piercing, anti-approach pressure. |
| Fencing | `skill_fencing` | Speed, precision, vital strikes, off-hand parry tools. |
| Unarmed | `skill_unarmed` | Body-driven close combat; current catalog expansion pending. |

## Swords

Design fantasy: balance and mastery.

Candidate base items:

- `sword`
- `longsword`
- `greatsword`
- `katana`
- `scimitar`

Candidate trigger directions:

- bleed on crit;
- heavy strike on crit;
- true crit;
- cleave on crit;
- tempo or accuracy flow on hit.

## Macing

Design fantasy: inevitable force, control, and armor damage.

Candidate base items:

- `hatchet`
- `battle_axe`
- `mace`
- `warhammer`
- `flail`

Candidate trigger directions:

- heavy strike on crit;
- stun on crit;
- unblockable crit;
- armor crush on crit;
- concentration or Energy pressure on hit.

## Archery

Design fantasy: distance, burst, and projection of force.

Candidate base items:

- `shortbow`
- `longbow`
- `composite_bow`
- `heavy_crossbow`

Candidate trigger directions:

- evasive shot;
- heavy strike on crit;
- stun or knockback;
- piercing crit;
- armor pierce on hit.

## Polearms

Design fantasy: reach and distance control.

Candidate base items:

- `spear`
- `pike`
- `halberd`
- `quarterstaff`
- `trident`

Candidate trigger directions:

- piercing crit;
- heavy strike on crit;
- stun on crit;
- knockdown on hit;
- keep-distance on hit;
- entangle or root-like pressure.

## Fencing

Design fantasy: speed, precision, and close control.

Candidate base items:

- `knife`
- `dagger`
- `stiletto`
- `rapier`
- `main_gauche`
- `katar`

Candidate trigger directions:

- bleed on hit;
- bleed on crit;
- piercing crit;
- true crit;
- counter on parry;
- vital trace or vital strike on crit.

## Verification Before Implementation

Before turning any candidate into runtime work, verify:

- base item id exists or should be added;
- related skill id exists in the skill catalog;
- trigger id exists in combat catalog or needs a new catalog entry;
- modifier fields exist and are consumed by resolver or intended future systems;
- combat log text exists or is planned;
- tests cover item catalog loading and combat projection.
