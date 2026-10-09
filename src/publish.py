from . import buffer, config


def publish_draft(draft):
    """Returns {platform: {"ok": bool, "detail": str}}."""
    results = {}
    try:
        channels = buffer.channel_map()
    except Exception as e:
        return {p: {"ok": False, "detail": f"Buffer channels failed: {e}"} for p in config.PLATFORMS}
    image_path = (draft.get("image") or {}).get("path")
    image_url = f"https://raw.githubusercontent.com/{config.REPO}/{config.BRANCH}/{image_path}" if image_path else None
    for p in config.PLATFORMS:
        try:
            if p not in channels:
                raise RuntimeError("channel not connected in Buffer")
            if p == "instagram" and not image_url:
                raise RuntimeError("Instagram needs an image and none was generated")
            post = buffer.create_post(channels[p], draft["posts"][p], image_url)
            results[p] = {"ok": True, "detail": f"queued {post.get('id')} due {post.get('dueAt')}"}
        except Exception as e:
            results[p] = {"ok": False, "detail": str(e)[:300]}
    return results
