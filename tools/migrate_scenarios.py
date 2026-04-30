import json
import os
import re

SOURCE_FILE = "src/backend/features/scenario/resources/json/tutorial_arrival.json"
TARGET_DIR = "src/backend/features/scenario/resources/json/awakening_rift"

def migrate():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)

    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Extract Master
    master = data.get("master", {})
    master["display_name"] = "ПРОБУЖДЕНИЕ В РАЗЛОМЕ"
    with open(f"{TARGET_DIR}/master.json", 'w', encoding='utf-8') as f:
        json.dump(master, f, indent=2, ensure_ascii=False)

    # 2. Extract and Process Nodes
    nodes = data.get("nodes", [])

    # Split into logical chunks
    chunks = {
        "start": ["rift_entry_01", "crash_sequence_02"],
        "bridge": [],
        "events": []
    }

    processed_nodes = []
    for node in nodes:
        # CLEANUP LOGIC
        original_text = node.get("text_content", "")

        # Split text from system messages
        # Pattern: looks for [#sys_actor]: ... or just CAPS lines at the end
        system_messages = []

        # Extract [#sys_actor] style
        sys_actor_matches = re.findall(r"\[#sys_actor\]:\s*(.*?)(?=\n|$)", original_text)
        system_messages.extend(sys_actor_matches)

        # Remove tags from text
        clean_text = re.sub(r"\[#sys_actor\]:\s*.*?\n?", "", original_text).strip()

        # Look for CAPITALIZED alerts (CRITICAL_...)
        alerts = re.findall(r"\b[A-Z_]{5,}\b", clean_text)
        if alerts:
            system_messages.extend(alerts)
            for alert in alerts:
                clean_text = clean_text.replace(alert, "").strip()

        # Update node structure
        new_node = {
            "node_key": node["node_key"],
            "text": clean_text,
            "system_messages": system_messages,
            "actions": []
        }

        # Process actions (remove emojis)
        for act_id, act_data in node.get("actions_logic", {}).items():
            label = act_data.get("label", "")
            # Simple emoji stripping for now
            clean_label = re.sub(r'[^\w\s\?.,!-]', '', label).strip()

            new_node["actions"].append({
                "action_id": act_id,
                "label": clean_label,
                "icon": "default", # Placeholder for later
                "to_node": act_data.get("to_node")
            })

        processed_nodes.append(new_node)

    # For now, let's just save nodes in manageable chunks of 20
    for i in range(0, len(processed_nodes), 20):
        chunk = processed_nodes[i:i+20]
        chunk_name = f"nodes_part_{i//20 + 1}.json"
        with open(f"{TARGET_DIR}/{chunk_name}", 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)

    print(f"Migration complete! Files created in {TARGET_DIR}")

if __name__ == "__main__":
    migrate()
