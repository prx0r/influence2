from __future__ import annotations

from .base import Observation


PLATFORM_URLS = {
    "x": "https://x.com/i/flow/signup",
    "instagram": "https://www.instagram.com/accounts/emailsignup/",
    "tiktok": "https://www.tiktok.com/signup",
    "youtube": "https://www.youtube.com/",
    "pinterest": "https://business.pinterest.com/",
    "bluesky": "https://bsky.app/",
    "github": "https://github.com/signup",
}


class SocialConnector:
    kind = "social"

    def observe(self, desired: dict) -> Observation:
        platform = str(desired.get("platform", "social")).lower()
        handle = desired.get("handle")
        state = desired.get("state", "unknown")
        required = desired.get("required", True)
        kit = desired.get("kit")
        if not required:
            return Observation("READY", f"{platform} is optional", observed={"required": False})
        if handle and state == "connected":
            return Observation("READY", f"{platform} @{handle} recorded as connected",
                               observed={"platform": platform, "handle": handle, "source": "passport"})
        signup_url = (kit or {}).get("signup_url") or PLATFORM_URLS.get(platform, "")
        handle_disp = f"@{handle}" if handle else "brand handle"
        if kit:
            title = f"Claim {kit.get('label', platform)} @{kit.get('handle', handle or '')}"
            instructions = kit.get("instructions") or (
                f"Open {kit.get('signup_url', signup_url)}, claim {handle_disp}, "
                f"follow the onboarding kit. Verification, CAPTCHA and legal acceptance remain human steps."
            )
            bio = kit.get("bio") or ""
            pin = kit.get("pin_post") or ""
            extra = ""
            if bio:
                extra += f"\n\nBio:\n{bio}"
            if pin:
                extra += f"\n\nPin:\n{pin}"
            if kit.get("website"):
                extra += f"\nWebsite: {kit['website']}"
            if kit.get("email"):
                extra += f"\nEmail: {kit['email']}"
            instructions = instructions + extra
            priority = int(kit.get("priority", 60))
            estimate = int(kit.get("estimate_seconds", 180))
        elif handle:
            title = f"Confirm {platform} {handle_disp}"
            instructions = (
                f"Open {platform}, confirm the account is accessible, then mark it connected "
                f"in the passport. Steve does not bypass login verification or CAPTCHA."
            )
            priority = 55
            estimate = 45
        else:
            title = f"Create {platform} account"
            instructions = (
                f"Create the {platform} account using the project's canonical handle/bio/avatar. "
                f"Verification, CAPTCHA and legal acceptance remain human steps."
            )
            priority = 60
            estimate = 90
        return Observation(
            "UNKNOWN" if handle else "MISSING",
            f"{platform} {handle_disp} exists in passport but is not confirmed connected"
            if handle else f"{platform} account missing",
            observed={"platform": platform, "handle": handle},
            executor="HUMAN",
            human_title=title,
            human_instructions=instructions,
            human_url=signup_url,
            estimate_seconds=estimate,
            priority=priority,
        )
