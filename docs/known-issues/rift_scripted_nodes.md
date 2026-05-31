# Resolved: scripted rift nodes launch combat

Scripted rift combat nodes are no longer a known issue.

Nodes whose `role_fit`/`tags` contain `boss`, `crystal_guard`,
`objective_gate`, `story_combat`, `key_combat`, or `crystal_chamber` are seeded
as required `node_entry` combat events by `NodeEventSeeder`.

These nodes still suppress transition combat on the approach so players do not
receive two fights in a row. Victory is resolved through the normal
`node_entry` event path; mob loot remains part of the common combat/loot
pipeline.
