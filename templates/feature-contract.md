# Feature contract

> One contract per accepted feature. A feature is not "done" because the code
> compiles. It is done when the contract and its evidence are satisfied.

## Identity

- **Feature:**
- **Brief section:**
- **Owner / date:**
- **Disposition:** accepted / deferred / unsupported / blocked

## Player outcome

- **What the player can do that they could not do before:**
- **How it sounds or behaves:**
- **How it fails visibly and safely:**

## Dependencies and interactions

- **Other features:**
- **Platform/API/HAL changes (if any):**
- **Persistence/version impact:**
- **MIDI/clock impact:**

## Parameter and event semantics

- **Parameters, ranges, defaults, curves, units:**
- **Note/event ordering and ownership:**
- **Voice allocation and stealing:**
- **Sustain/panic behaviour:**

## Bounds and resources

- **Maximum voices/events/effects:**
- **Per-sample and per-block operations:**
- **RAM, flash, stack, pool:**
- **Overflow/overload policy:**
- **Division, shift, and range analysis:**

## Files and interfaces

- **Candidate files:**
- **Public contract/header:**
- **State owner and publication rule:**
- **Forbidden dependencies (malloc, float, flash, display in audio):**

## Verification

- **Host vector(s):**
- **Browser vector (if applicable):**
- **Target package check:**
- **Physical timing/device check:**
- **Tolerance/metric:**
- **Evidence artifact:**

## Risks and fallback

- **Assumptions/open research:**
- **Safe experiment and stop criterion:**
- **Smaller alternative:**
- **Rollback:**
