from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.shared.schemas.city_services import CityServiceScreenEnum, CityServiceUIPayloadDTO


def test_city_service_viewport_renders_clickable_npc_contact():
    env = Environment(
        loader=FileSystemLoader("src/frontend/templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("game/domains/city_services/viewport/main.html")
    city_service = CityServiceUIPayloadDTO(
        service_id="svc_portal_hub",
        service_type="portal",
        location_id="52_52",
        screen=CityServiceScreenEnum.MAIN,
        title="Площадь Рунного Круга",
        description="Описание",
        metadata={
            "npc": {
                "id": "portal_first_contact",
                "name": "Проводник Круга",
                "role": "FIRST CONTACT",
                "stage_position": "bottom-right",
                "dialogue_quest_key": "awakening_rift",
            }
        },
    )

    rendered = template.render(city_service=city_service, char_id=7)

    assert "city-service-npc-contact--bottom-right" in rendered
    assert "Проводник Круга" in rendered
    assert '"action": "start_dialogue"' in rendered
    assert '"service_id": "svc_portal_hub"' in rendered
    assert '"location_id": "52_52"' in rendered
