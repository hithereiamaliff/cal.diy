#!/usr/bin/env python3
"""
TechMavie Booking branding for Cal.diy.

Run from the repository root BEFORE `docker build` (the CI workflow does this).
Upstream files are patched at build time only, so syncing the fork with
calcom/cal.diy never causes merge conflicts.

Logo policy: uses ONLY the official TechMavie Digital logo
(https://techmavie.digital/logo.png, checksum-verified). Images are only
cropped and resized, never recoloured or redrawn.

Every patch must match, otherwise the build fails loudly, so an upstream
change can never silently drop the branding.
"""
import base64
import hashlib
import io
import json
import pathlib
import sys
import urllib.request

from PIL import Image

LOGO_URL = "https://techmavie.digital/logo.png"
LOGO_SHA256 = "5f7bfb140efdfa90342a000d493fb638002b7fbdeffb316962d816dd0cba9da7"

APP_NAME = "TechMavie Booking"
COMPANY = "TechMavie Digital"
SUPPORT_EMAIL = "bookings@techmavie.digital"
WEBSITE = "https://techmavie.digital"
BOOKING_URL = "https://book.techmavie.digital"
NAVY = "#181F39"          # background colour of the official logo
BRAND_LIGHT = "#2563eb"   # techmavie.digital primary (Tailwind blue-600)
BRAND_DARK = "#3b82f6"    # blue-500 for dark theme contrast

ROOT = pathlib.Path(".")
PUB = ROOT / "apps/web/public"
RESAMPLE = Image.LANCZOS

# Crop boxes measured on the 1024x1024 original.
# WORD: cut through the two fully empty bands above/below the text
#       (rows 400-423 and 664-682) so no letter or circuit dot is clipped.
WORD_BOX = (80, 411, 940, 673)
# SQUARE: the full logo artwork (text + circuits) centred, minimal margin.
SQUARE_BOX = (67, 79, 949, 961)


def fail(msg: str) -> None:
    print(f"::error::BRANDING: {msg}")
    sys.exit(1)


# ---------------------------------------------------------------- images ----
def load_logo() -> Image.Image:
    req = urllib.request.Request(LOGO_URL, headers={"User-Agent": "techmavie-branding/1.0"})
    raw = urllib.request.urlopen(req, timeout=60).read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != LOGO_SHA256:
        fail(f"logo checksum mismatch ({digest}); refusing to use an unverified logo")
    return Image.open(io.BytesIO(raw)).convert("RGB")


def write_png(im: Image.Image, rel: str, size=None) -> None:
    path = PUB / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    (im.resize(size, RESAMPLE) if size else im).save(path, optimize=True)
    print(f"  image  {rel} {size or im.size}")


def svg_wrapper(im: Image.Image, size) -> str:
    buf = io.BytesIO()
    im.resize(size, RESAMPLE).save(buf, "PNG", optimize=True)
    data = base64.b64encode(buf.getvalue()).decode()
    w, h = size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{data}"/></svg>'
    )


def build_images() -> None:
    src = load_logo()
    word = src.crop(WORD_BOX)
    square = src.crop(SQUARE_BOX)

    def word_size(h: int):
        return (round(word.width * h / word.height), h)

    # Header / login wordmark (rendered at h-4/h-5 -> supply 8x density)
    write_png(word, "techmavie-logo-word.png", word_size(160))
    # Square icon used by the sidebar and OAuth screens
    write_png(square, "techmavie-icon.png", (256, 256))

    # Overwrite upstream icon files in place (same names Cal.diy references)
    for name, px in {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
        "android-chrome-256x256.png": 256,
        "android-chrome-384x384.png": 384,
        "android-chrome-512x512.png": 512,
        "mstile-70x70.png": 70,
        "mstile-144x144.png": 144,
        "mstile-150x150.png": 150,
        "mstile-310x310.png": 310,
    }.items():
        write_png(square, name, (px, px))
    square.resize((256, 256), RESAMPLE).save(PUB / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print("  image  favicon.ico [16,32,48]")

    # Email header logo (displayed at 92x28, supplied at 2x)
    write_png(word, "emails/logo.png", word_size(56))
    write_png(word, "emails/CalLogo@2x.png", word_size(56))

    # Upstream SVG logos still referenced in a few places -> same logo, wrapped
    for name in ("cal-logo-word.svg", "cal-logo-word-dark.svg", "cal-logo-word-black.svg",
                 "calcom-logo-white-word.svg"):
        (PUB / name).write_text(svg_wrapper(word, word_size(80)))
        print(f"  image  {name} (wrapped wordmark)")
    for name in ("cal-com-icon.svg", "cal-com-icon-white.svg"):
        (PUB / name).write_text(svg_wrapper(square, (112, 112)))
        print(f"  image  {name} (wrapped icon)")


# ----------------------------------------------------------------- code -----
def patch(rel: str, pairs) -> None:
    path = ROOT / rel
    if not path.exists():
        fail(f"{rel} not found (upstream moved it?)")
    text = path.read_text()
    for old, new in pairs:
        if old not in text:
            fail(f"{rel}: expected text not found: {old!r}")
        text = text.replace(old, new)
    path.write_text(text)
    print(f"  patch  {rel} ({len(pairs)} edits)")


def build_code() -> None:
    patch("packages/lib/constants.ts", [
        ('process.env.NEXT_PUBLIC_WEBSITE_URL) || "https://cal.com"',
         f'process.env.NEXT_PUBLIC_WEBSITE_URL) || "{BOOKING_URL}"'),
        ('process.env.NEXT_PUBLIC_APP_NAME || "Cal.diy"', f'process.env.NEXT_PUBLIC_APP_NAME || "{APP_NAME}"'),
        ('process.env.NEXT_PUBLIC_SUPPORT_MAIL_ADDRESS || "help@cal.com"',
         f'process.env.NEXT_PUBLIC_SUPPORT_MAIL_ADDRESS || "{SUPPORT_EMAIL}"'),
        ('process.env.NEXT_PUBLIC_COMPANY_NAME || "Cal.com, Inc."',
         f'process.env.NEXT_PUBLIC_COMPANY_NAME || "{COMPANY}"'),
        ('process.env.NEXT_PUBLIC_SENDER_ID || "Cal"', 'process.env.NEXT_PUBLIC_SENDER_ID || "TechMavie"'),
        ('process.env.NEXT_PUBLIC_SENDGRID_SENDER_NAME || "Cal.diy"',
         f'process.env.NEXT_PUBLIC_SENDGRID_SENDER_NAME || "{APP_NAME}"'),
        ('LOGO = "/calcom-logo-white-word.svg"', 'LOGO = "/techmavie-logo-word.png"'),
        ('LOGO_DARK = "/cal-logo-word-black.svg"', 'LOGO_DARK = "/techmavie-logo-word.png"'),
        ('LOGO_ICON = "/cal-com-icon-white.svg"', 'LOGO_ICON = "/techmavie-icon.png"'),
        ('ROADMAP = "https://cal.com/roadmap"', f'ROADMAP = "{WEBSITE}"'),
        ('DESKTOP_APP_LINK = "https://cal.com/download"', f'DESKTOP_APP_LINK = "{WEBSITE}"'),
        ('POWERED_BY_URL = "https://go.cal.com/booking"', f'POWERED_BY_URL = "{WEBSITE}"'),
        ('DOCS_URL = "https://cal.com/docs"', f'DOCS_URL = "{WEBSITE}"'),
        ('DEVELOPER_DOCS = "https://developer.cal.com"', f'DEVELOPER_DOCS = "{WEBSITE}"'),
        ('DEFAULT_LIGHT_BRAND_COLOR = "#292929"', f'DEFAULT_LIGHT_BRAND_COLOR = "{BRAND_LIGHT}"'),
        ('DEFAULT_DARK_BRAND_COLOR = "#fafafa"', f'DEFAULT_DARK_BRAND_COLOR = "{BRAND_DARK}"'),
    ])

    # Logo component: keep the logo's real colours in dark mode (no invert)
    patch("packages/ui/components/logo/Logo.tsx", [
        ('"mx-auto w-9 dark:invert"', '"mx-auto w-9 rounded-md"'),
        ('"h-5 w-auto", "dark:invert"', '"h-5 w-auto", "rounded-sm"'),
        ('alt="Cal.diy"', f'alt="{APP_NAME}"'),
        ('title="Cal.diy"', f'title="{APP_NAME}"'),
    ])

    patch("apps/web/pages/_document.tsx", [
        ('name="msapplication-TileColor" content="#ff0000"', f'name="msapplication-TileColor" content="{NAVY}"'),
    ])
    patch("apps/web/modules/videos/views/videos-single-view.tsx", [
        ("/cal-logo-word-dark.svg", "/techmavie-logo-word.png"),
    ])
    patch("apps/web/modules/auth/oauth2/authorize-view.tsx", [
        ('"/cal-com-icon.svg"', '"/techmavie-icon.png"'),
    ])
    # Email header logo slot: 89x19 -> 92x28 (matches the wordmark ratio)
    patch("packages/emails/src/components/EmailBodyLogo.tsx", [
        ('width: "89px"', 'width: "92px"'),
        ('height="19"', 'height="28"'),
        ('height: "19px"', 'height: "28px"'),
        ('width="89"', 'width="92"'),
    ])

    # Avatars: give every upload a fresh URL so browsers never show a stale photo,
    # and shorten the avatar cache from 24h to 5 min.
    patch("packages/lib/server/avatar.ts", [
        ("  const objectKey = existing?.objectKey ?? uuidv4();",
         "  // TechMavie: always issue a new key so a new upload gets a new URL\n"
         "  void existing;\n"
         "  const objectKey = uuidv4();"),
        ("      data: processedData,\n      // Don't update objectKey - keep existing to preserve URLs\n",
         "      data: processedData,\n      objectKey,\n"),
    ])
    patch("apps/web/app/api/avatar/[uuid]/route.ts", [
        ('"Cache-Control": "max-age=86400"', '"Cache-Control": "public, max-age=300"'),
    ])

    # Onboarding: Teams were removed from Cal.diy - hide the paid "With my team" plan
    patch("apps/web/modules/onboarding/getting-started/onboarding-view.tsx", [
        ('    if (plan.id === "organization") {\n      return false;\n    }',
         '    if (plan.id === "organization" || plan.id === "team") {\n      return false;\n    }'),
    ])
    import re
    badge_re = re.compile(r'("onboarding_plan_team_badge":\s*)"(?:[^"\\\\]|\\\\.)*"')
    for path in sorted((ROOT / "packages/i18n/locales").glob("*/common.json")):
        text = path.read_text()
        new_text = badge_re.sub(r'\1""', text)
        if new_text != text:
            path.write_text(new_text)
    print("  patch  onboarding team plan hidden, price text removed")

    # HitPay: the checkout lives on checkout.hit-pay.com (an external site). Next's
    # router.replace() cannot navigate cross-origin and crashes the payment page,
    # so do a real browser redirect instead.
    patch("apps/web/components/apps/hitpay/HitpayPaymentComponent.tsx", [
        ("        router.replace(parsedData.data.url);\n",
         "        window.location.replace(parsedData.data.url);\n"),
    ])

    # Single-owner instance: bake "signups disabled" into the build
    # (NEXT_PUBLIC_* values are inlined at build time, so .env alone is not enough)
    patch("Dockerfile", [
        ("ARG CSP_POLICY\n", "ARG CSP_POLICY\nARG NEXT_PUBLIC_DISABLE_SIGNUP=true\n"),
        ("  BUILD_STANDALONE=true \\\n",
         "  BUILD_STANDALONE=true \\\n  NEXT_PUBLIC_DISABLE_SIGNUP=$NEXT_PUBLIC_DISABLE_SIGNUP \\\n"),
    ])

    manifest_path = PUB / "site.webmanifest"
    manifest = json.loads(manifest_path.read_text())
    manifest.update({
        "name": APP_NAME,
        "short_name": "TechMavie",
        "description": f"Book a session with {COMPANY}.",
        "theme_color": NAVY,
        "background_color": NAVY,
    })
    manifest_path.write_text(json.dumps(manifest, indent=4) + "\n")
    print("  patch  apps/web/public/site.webmanifest")

    # UI text: "Cal.diy" -> app name, in every language
    locales = sorted((ROOT / "packages/i18n/locales").glob("*/common.json"))
    if not locales:
        fail("no locale files found")
    total = 0
    for path in locales:
        text = path.read_text()
        n = text.count("Cal.diy")
        if n:
            path.write_text(text.replace("Cal.diy", APP_NAME))
            total += n
    if total == 0:
        fail("no 'Cal.diy' strings found in locales (upstream changed?)")
    print(f"  patch  {len(locales)} locale files ({total} strings)")


if __name__ == "__main__":
    print("TechMavie Booking branding")
    build_images()
    build_code()
    print("Branding applied OK")
