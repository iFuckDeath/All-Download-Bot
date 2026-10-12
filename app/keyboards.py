from aiogram.utils.keyboard import InlineKeyboardBuilder

def home(custom_emoji_id=""):
    b = InlineKeyboardBuilder()
    b.button(text="⬇️ Download", callback_data="home:download", style="primary",
             icon_custom_emoji_id=custom_emoji_id or None)
    b.button(text="📊 My stats", callback_data="home:stats", style="success")
    b.button(text="🌐 Sources", callback_data="home:sources")
    b.button(text="❔ Help", callback_data="home:help")
    b.adjust(2, 2)
    return b.as_markup()

def formats(job_id, options, custom_emoji_id=""):
    b = InlineKeyboardBuilder()
    for i, option in enumerate(options[:5]):
        b.button(text=option["label"], callback_data=f"fmt:{job_id}:{i}",
                 style="primary" if i == 0 else "success",
                 icon_custom_emoji_id=(custom_emoji_id or None) if i == 0 else None)
    b.button(text="✖ Cancel", callback_data=f"cancel:{job_id}", style="danger")
    b.adjust(2, 2, 1)
    return b.as_markup()
