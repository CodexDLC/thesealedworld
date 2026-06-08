from pathlib import Path


def test_controlled_pass_button_posts_empty_combat_move_without_feint() -> None:
    template = Path("src/frontend/templates/game/domains/combat/viewport/main.html").read_text(encoding="utf-8")
    pass_branch = template.split("{% if combat_screen.primary_attack.kind == 'pass' %}", maxsplit=1)[1].split(
        "{% else %}", maxsplit=1
    )[0]

    assert 'hx-post="/game/combat/move"' in pass_branch
    assert 'action": "pass"' in pass_branch
    assert '"target_id": {{ primary_target_id | tojson }}' in pass_branch
    assert "feint_id" not in pass_branch
    assert 'hx-get="/game/session/state/combats' not in pass_branch
