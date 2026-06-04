"""Studio shell — the base layout, header, source switcher, landing page.

The base template (`templates/studio/base_studio.html`) extends the prod
frontend's `site/base_cabinet.html` so the design system, fonts, colour
tokens, and admin CSS bundle are shared. The shell only adds:

- Source Switcher dropdown in the header.
- LOCAL / PROD READ-ONLY badge next to the logo.
- A minimal home page that confirms wiring is alive.
"""
