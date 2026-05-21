---
name: turnbasedmmorpg-news-management
description: Skill for writing, formatting, and publishing devlogs, news, and patch notes for The Sealed World. Contains official links and HTML/CSS templates.
---

# TurnBasedMMORPG News Management

This skill provides guidelines for creating, formatting, and publishing game updates, announcements, and patch notes for "The Sealed World" (Запечатанный Мир).

## Official Community Resources

Use these links whenever generating news footers or Call to Action (CTA) blocks:

- **Official Web Portal:** `https://thesealedworld.com`
- **Game client:** `https://play.thesealedworld.com`
- **Telegram News Channel:** `https://t.me/thesealedworld`
- **Telegram Discussion Group:** `https://t.me/+bxwrVS_9Wo00ZTky`

## News Database Reference

Frontend `Article` models are defined in `src/frontend/features/news/models/article.py` with schema `site`:
- `slug` (String, unique) - URL friendly identifier (e.g. `launch-pre-alpha-0-1-0`).
- `title` (String) - Article Title.
- `preview` (String) - Brief card description (max 400 chars).
- `body` (Text) - Raw HTML content of the article (rendered with `{{ article.body | safe }}`).
- `cover_image` (String, optional) - Image path.
- `is_published` (Boolean) - Publication status.

## Content & HTML Formatting Rules

Since `article.body` is rendered with `| safe`, all news content must be structured using clean HTML tags. Do not output raw markdown in the body field.

### Essential HTML Structure:

1. **Paragraphs:** Wrap text blocks in `<p>` tags to ensure standard site line breaks.
   ```html
   <p>Text goes here...</p>
   ```

2. **Subheadings:** Use standard `<h3>` for feature sections.
   ```html
   <h3>🖥️ Интерфейс и Фронтенд:</h3>
   ```

3. **Lists:** Wrap lists in `<ul>` and `<li>` with semantic emojis for micro-design.
   ```html
   <ul>
     <li>👤 <strong>Регистрация:</strong> Текст...</li>
     <li>⚔️ <strong>Боевая система:</strong> Текст...</li>
   </ul>
   ```

4. **Style-consistent Links:** Apply design system colors to links for a premium feel.
   ```html
   <a href="URL" target="_blank" style="font-weight: bold; color: #3b82f6;">Текст ссылки</a>
   ```

5. **Design System Buttons (if prominent CTA is needed):**
   ```html
   <a href="URL" target="_blank" class="btn-node ghost sm"><span>Текст кнопки</span></a>
   ```
