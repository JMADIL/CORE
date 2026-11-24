"""Limit public-demo spending and isolate the owner's shared workspace data."""
import json

from core.storage.errors import SessionAccessDenied

GENERATIONS = {
    "creative_generate_image", "creative_edit_image", "creative_generate_video",
    "creative_generate_speech", "creative_generate_in_flow",
}
SHARED_TOOLS = GENERATIONS | {
    "creative_list_voices", "creative_get_flow_node_types", "creative_get_model_guide",
    "creative_get_model_schema", "creative_get_flow_run_status", "creative_show_flow_results",
    "creative_get_flow", "creative_get_flow_node",
}
_RESOURCE_KEYS = {"flow_id": "flow", "node_id": "node", "session_id": "session",
                  "generation_id": "generation", "voice_id": "voice", "voice": "voice", "view_state_id": "view"}


def resource_key(kind, value, owner):
    # Public library voices can be selected independently by multiple visitors.
    return f"voice:{owner}:{value}" if kind == "voice" else f"{kind}:{value}"


def guard_call(name, arguments, owner, store):
    if store is None or not owner:
        raise SessionAccessDenied("The shared media demo is not ready.")
    name = name.removeprefix("elevenlabs_")
    if name not in SHARED_TOOLS:
        raise SessionAccessDenied("This operation is not available in the shared demo.")
    args = dict(arguments)
    if name in GENERATIONS:
        # Hosted creative tools default to multiple variations. Enforce the
        # demo's single result even when discovery omits optional schema fields.
        args["generations_count"] = 1
    if name in {"creative_get_flow", "creative_get_flow_node", "creative_get_flow_run_status", "creative_show_flow_results"} and not args.get("flow_id"):
        raise SessionAccessDenied("Choose media created in this browser first.")

    def check(values):
        for key, value in values.items():
            if key == "connect_from":
                if value and not args.get("flow_id"):
                    raise SessionAccessDenied("A reference must belong to your media flow.")
                for item in value or []:
                    store.check_media_resource("node:" + str(item), owner)
            elif key in _RESOURCE_KEYS and value:
                store.check_media_resource(resource_key(_RESOURCE_KEYS[key], value, owner), owner)
            elif key.removesuffix("s") in _RESOURCE_KEYS and isinstance(value, list):
                kind = _RESOURCE_KEYS[key.removesuffix("s")]
                for item in value:
                    store.check_media_resource(resource_key(kind, item, owner), owner)
            elif isinstance(value, dict):
                check(value)
    check(args)
    if name == "creative_list_voices":
        # This filter selects public library voices, not the owner's voice list.
        args["voice_category"] = "professional"
    return args


def remember_results(text, owner, store):
    try:
        result = json.loads(text)
    except (ValueError, TypeError):
        return
    if not isinstance(result, dict):
        return
    rows = [result]
    # Only parse provider resource fields, never prompts or arbitrary nested text.
    for key in ["results", "media", "pending", "generations", "voices"]:
        rows.extend(row for row in (result.get(key) or []) if isinstance(row, dict))
    for row in rows:
        for key, kind in _RESOURCE_KEYS.items():
            if isinstance(row.get(key), str):
                store.remember_media_resource(resource_key(kind, row[key], owner), owner)
        if row in (result.get("generations") or []) and isinstance(row.get("id"), str):
            store.remember_media_resource("generation:" + row["id"], owner)
        for key in ["session_ids", "node_ids"]:
            for value in (row.get(key) or []):
                if isinstance(value, str):
                    store.remember_media_resource(_RESOURCE_KEYS[key[:-1]] + ":" + value, owner)
