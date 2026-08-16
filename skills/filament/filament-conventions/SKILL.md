---
name: filament-conventions
description: Follow Filament conventions when building resources, forms, tables, actions, and widgets. Use when adding or changing Filament admin panels.
---

# Filament Conventions

Use this when building or changing Filament admin panel code.

## Detect the version first

```bash
composer show filament/filament | grep versions
```

v3 and v4 have different APIs — check before writing or copying code:

- v4 unifies forms and infolists under `Filament\Schemas\Schema`; v3 uses `Filament\Forms\Form` and `Filament\Infolists\Infolist`.
- Component namespaces, layout components, and many method signatures moved in v4.
- Plugins are version-specific; a v3 plugin will not install on v4 (see `filament-plugin-first`).

Match the project's installed major version. Never mix v3 and v4 snippets.

## Resource Structure

- One resource per model, with a clear singular name.
- Keep form and table definitions in dedicated methods or classes.
- Use relation managers for related data, not custom inline tables.
- Prefer policies for authorization over inline gate checks.

## Forms and tables

- Build forms with schema components, not raw HTML.
- Use built-in columns and filters before custom ones.
- Define actions, bulk actions, and filters declaratively.
- Keep table queries efficient; eager load and defer heavy columns.

## Actions and tenancy

- Implement custom actions as action classes, not inline closures.
- Use action modals for confirmations and multi-step flows.
- Centralize tenant scope in the panel provider or middleware.
- Apply tenant constraints at the query level, not scattered in resources.

## Verification

- Run affected Pest/feature tests.
- Verify the panel renders without errors at `php artisan serve`.
- Check that authorization policies still enforce expected access.
