# Shared Layout Refactor Notes

Date: 2026-06-29

## Scope

This refactor adjusts the shared Django layout after the earlier dashboard
shell redesign. The goal is to keep the full-width header and footer pattern
while making the top area more compact, removing the municipality searchbox
from the navbar, and standardizing content spacing across the main public
pages.

## What Changed

- Removed the municipality searchbox from the shared navbar.
- Kept the navigation limited to:
  `Início`, `Dados`, `Relatórios`, `Produtos`, `Equipe`, and `Sobre nós`.
- Moved the only municipality searchbox to the home body section:
  `Encontre os níveis de alerta da sua cidade`.
- Reduced shared header height by tightening:
  - header paddings
  - logo maximum size
  - partner logo maximum size
  - navbar row spacing
- Removed boxed styling from partner logos so they read as supporting brands
  rather than primary callouts.
- Narrowed the general content shell to a more readable range and normalized
  direct nested `.container` and `.container-fluid` wrappers inside
  `.site-content`.
- Kept full-width footer behavior while tightening internal spacing.

## Searchbox Strategy

- Select2 assets remain globally loaded in `base.html`.
- Searchbox initialization remains centralized in `base.html`.
- Initialization now targets generic `.js-select2[data-placeholder]` elements
  instead of assuming a navbar-specific search slot.
- The shared searchbox template now uses generic municipality-search wrapper
  classes so it can be embedded in content sections without navbar coupling.

## Stability Fixes

The remaining layout-shift risk after the prior redesign came from a searchbox
implementation that still assumed the shared header/nav area. This refactor
removes that assumption by:

- removing the navbar search placement
- keeping a single search instance on the home page
- keeping Select2 initialization idempotent
- cleaning malformed home-section markup introduced during the move

## Validation Performed

- `python AlertaDengue/manage.py check`
- `git diff`
- `git status`
- Live HTML fetch checks against `http://188.245.39.97:8080/`

## Remaining Limitation

This environment did not provide a usable browser runner, so responsive
validation was limited to code review and live HTML inspection rather than
full viewport screenshots or interactive collapse testing.
