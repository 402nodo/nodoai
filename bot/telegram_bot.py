"""
Nodo Telegram Bot - AI-Powered Prediction Market Analysis
Uses Groq (Llama 3.1 70B) for real AI analysis
"""
import os
import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import Optional, List
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from ai_analyzer import AIAnalyzer, AIAnalysis
from delta_scanner import DeltaScanner, DeltaOpportunity

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GAMMA_URL = "https://gamma-api.polymarket.com"

# AI Analyzer
ai = AIAnalyzer()

# Scanners
delta_scanner = DeltaScanner()

# Cache
cached_opportunities: List[dict] = []
cached_delta: List[DeltaOpportunity] = []
subscribers: set = set()


class MarketScanner:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.all_opportunities = []  # Full list
    
    async def scan(self, min_prob: float = 0.95, limit: int = 300, shuffle: bool = True) -> List[dict]:
        global cached_opportunities
        
        try:
            # Add random offset to get different markets each time
            offset = random.randint(0, 100)
            response = await self.client.get(
                f"{GAMMA_URL}/markets",
                params={
                    "limit": limit, 
                    "active": "true", 
                    "closed": "false",
                    "offset": offset
                }
            )
            response.raise_for_status()
            markets = response.json()
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return cached_opportunities
        
        opportunities = []
        for market in markets:
            opp = self._parse_market(market, min_prob)
            if opp:
                opportunities.append(opp)
        
        # Sort by APY
        opportunities.sort(key=lambda x: x["apy"], reverse=True)
        
        # Store full list
        self.all_opportunities = opportunities.copy()
        
        # Return randomized selection from top 25
        if shuffle and len(opportunities) > 7:
            top_pool = opportunities[:25]  # Take top 25 by APY
            random.shuffle(top_pool)
            result = top_pool[:7]  # Show 7 random from top 25
            # Re-sort by APY for display
            result.sort(key=lambda x: x["apy"], reverse=True)
            cached_opportunities = result
            return result
        
        cached_opportunities = opportunities[:7]
        return opportunities[:7]
    
    def _parse_market(self, market: dict, min_prob: float) -> Optional[dict]:
        try:
            outcomes_raw = market.get("outcomes", '["Yes", "No"]')
            prices_raw = market.get("outcomePrices", '["0.5", "0.5"]')
            
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            prices = [float(p) for p in (json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw)]
            
            if len(outcomes) != 2:
                return None
            
            yes_price, no_price = prices[0], prices[1]
            
            if yes_price >= min_prob:
                outcome, buy_price = "YES", yes_price
            elif no_price >= min_prob:
                outcome, buy_price = "NO", no_price
            else:
                return None
            
            if buy_price >= 0.995:
                return None
            
            volume = float(market.get("volume", 0))
            if volume < 5000:
                return None
            
            liquidity = float(market.get("liquidity", 0))
            profit_pct = ((1.0 - buy_price) / buy_price) * 100
            
            end_date_str = market.get("endDate")
            if not end_date_str:
                return None
            
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                days = max(1, (end_date - datetime.now(timezone.utc)).days)
                end_formatted = end_date.strftime("%d %b %Y")
            except:
                days = 30
                end_formatted = "Unknown"
            
            if days > 60:
                return None
            
            apy = (profit_pct / days) * 365
            
            if buy_price >= 0.97:
                risk = "SAFE"
                risk_emoji = "🟢"
            elif buy_price >= 0.95:
                risk = "MODERATE"
                risk_emoji = "🟡"
            else:
                risk = "RISKY"
                risk_emoji = "🔴"
            
            slug = market.get("slug", market.get("id", ""))
            
            return {
                "id": str(market.get("id", "")),
                "question": market.get("question", ""),
                "outcome": outcome,
                "buy_price": buy_price,
                "profit_pct": round(profit_pct, 2),
                "days": days,
                "end_date": end_formatted,
                "apy": round(apy, 1),
                "volume": volume,
                "liquidity": liquidity,
                "risk": risk,
                "risk_emoji": risk_emoji,
                "url": f"https://polymarket.com/event/{slug}",
                "ai_analysis": None  # Will be filled on demand
            }
        except:
            return None


scanner = MarketScanner()


# ==================== FORMATTERS ====================

def format_welcome() -> str:
    has_ai = "ON" if OPENROUTER_API_KEY else "OFF"
    ai_status = "AI Analysis: " + has_ai
    return (
        "🤖 *NODO*\n"
        "AI-Powered Prediction Markets\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧠 {ai_status}\n\n"
        "Нахожу возможности и анализирую\n"
        "их с помощью *AI*\n\n"
        "*Выбери стратегию:*"
    )


def format_delta_menu() -> str:
    return (
        "🔄 *DELTA NEUTRAL*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Стратегия:*\n"
        "Находим логические ошибки рынка:\n\n"
        "Пример:\n"
        "• BTC $150K YES = $0.20\n"
        "• BTC $100K YES = $0.15 ❌\n\n"
        "Если BTC достигнет $150K, он *обязательно*\n"
        "достигнет $100K! Значит $100K YES\n"
        "должен стоить >= $150K YES\n\n"
        "*Профит:* Покупаем недооценённый"
    )


def format_yield_menu() -> str:
    return (
        "📈 *YIELD FARMING*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*Стратегия:*\n"
        "Покупаем исходы с высокой\n"
        "вероятностью (95%+)\n\n"
        "*AI анализирует:*\n"
        "• Реальность события\n"
        "• Риски и подводные камни\n"
        "• Рекомендацию BUY/SKIP\n\n"
        "*Выбери режим:*"
    )


def format_list(opps: List[dict], title: str) -> str:
    if not opps:
        return f"{title}\n\n❌ Ничего не найдено"
    
    text = f"{title}\n"
    text += f"Найдено: *{len(opps)}*\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, opp in enumerate(opps[:7], 1):
        q = opp['question'][:35] + "..." if len(opp['question']) > 35 else opp['question']
        
        text += (
            f"*{i}.* {opp['risk_emoji']} {q}\n"
            f"    {opp['outcome']} @ ${opp['buy_price']:.3f}\n"
            f"    💰 {opp['profit_pct']:.1f}% | 📈 {opp['apy']:.0f}% APY | ⏳ {opp['days']}д\n\n"
        )
    
    return text


def format_card_basic(opp: dict, idx: int) -> str:
    """Basic card without AI analysis."""
    return (
        f"{opp['risk_emoji']} *#{idx} {opp['question']}*\n\n"
        f"┌─ *СДЕЛКА*\n"
        f"│  Покупаем: *{opp['outcome']}* @ ${opp['buy_price']:.3f}\n"
        f"│  Вероятность: {opp['buy_price']*100:.1f}%\n"
        f"│  Профит: *{opp['profit_pct']:.2f}%*\n"
        f"│  APY: *{opp['apy']:.0f}%*\n"
        f"├─ *СРОКИ*\n"
        f"│  Резолюция: {opp['end_date']}\n"
        f"│  Осталось: {opp['days']} дней\n"
        f"├─ *ЛИКВИДНОСТЬ*\n"
        f"│  Volume: ${opp['volume']:,.0f}\n"
        f"│  Liquidity: ${opp['liquidity']:,.0f}\n"
        f"└─ Риск: {opp['risk']}\n\n"
        f"🔗 [Polymarket]({opp['url']})"
    )


def format_card_ai(opp: dict, idx: int, analysis: AIAnalysis) -> str:
    """Full card with AI analysis."""
    
    # Confidence emoji
    if analysis.confidence >= 75:
        conf_emoji = "🟢"
    elif analysis.confidence >= 50:
        conf_emoji = "🟡"
    else:
        conf_emoji = "🔴"
    
    # Recommendation emoji
    if "BUY" in analysis.recommendation.upper():
        rec_emoji = "✅"
    elif "SKIP" in analysis.recommendation.upper():
        rec_emoji = "❌"
    else:
        rec_emoji = "⚠️"
    
    text = (
        f"{opp['risk_emoji']} *#{idx} {opp['question']}*\n\n"
        f"┌─ *СДЕЛКА*\n"
        f"│  {opp['outcome']} @ ${opp['buy_price']:.3f} ({opp['buy_price']*100:.1f}%)\n"
        f"│  Профит: *{opp['profit_pct']:.2f}%* | APY: *{opp['apy']:.0f}%*\n"
        f"│  Резолюция: {opp['end_date']} ({opp['days']}д)\n"
        f"└─ Volume: ${opp['volume']:,.0f}\n\n"
    )
    
    # AI Analysis
    text += f"🧠 *AI АНАЛИЗ* {conf_emoji} {analysis.confidence}%\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += f"*Вердикт:*\n_{analysis.verdict}_\n\n"
    
    text += "*Почему:*\n"
    for r in analysis.reasons[:3]:
        text += f"• {r}\n"
    
    text += "\n*Риски:*\n"
    for r in analysis.risks[:2]:
        text += f"⚠️ {r}\n"
    
    text += f"\n{rec_emoji} *{analysis.recommendation}*\n\n"
    
    text += f"🔗 [Открыть на Polymarket]({opp['url']})"
    
    return text


# ==================== KEYBOARDS ====================

def get_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Yield Farming", callback_data="menu_yield")],
        [InlineKeyboardButton("🔄 Delta Neutral", callback_data="menu_delta")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")],
    ])


def get_delta_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Сканировать", callback_data="delta_scan")],
        [InlineKeyboardButton("« Назад", callback_data="menu_main")],
    ])


def format_delta_list(opps: List[DeltaOpportunity]) -> str:
    if not opps:
        return "🔄 *DELTA NEUTRAL*\n\n❌ Логических ошибок не найдено\n\nРынок эффективен!"
    
    text = f"🔄 *DELTA NEUTRAL*\n"
    text += f"Найдено: *{len(opps)}* ошибок\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, opp in enumerate(opps[:5], 1):
        text += f"*{i}. [{opp.topic}]* ⚠️\n"
        text += f"   {opp.logic_error}\n"
        text += f"   💰 Профит: *{opp.profit_potential:.1f}%*\n\n"
    
    return text


def format_delta_card(opp: DeltaOpportunity, idx: int) -> str:
    # Check if same event (arbitrage case)
    same_event = opp.event_a['id'] == opp.event_b['id']
    
    text = (
        f"🔄 *#{idx} DELTA NEUTRAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *Тема:* {opp.topic}\n"
        f"🎯 *Уверенность:* {opp.confidence}%\n\n"
    )
    
    # Explanation
    if opp.explanation:
        text += f"🧠 *ОБЪЯСНЕНИЕ:*\n{opp.explanation}\n\n"
    
    text += f"⚠️ *ОШИБКА:* _{opp.logic_error}_\n\n"
    
    if same_event:
        text += (
            f"📈 *СОБЫТИЕ:*\n"
            f"{opp.event_a['question'][:80]}\n"
            f"YES: ${opp.event_a['yes_price']:.2f} | NO: ${opp.event_a['no_price']:.2f}\n"
            f"Volume: ${opp.event_a['volume']:,.0f}\n\n"
        )
    else:
        text += (
            f"📈 *СОБЫТИЕ A:*\n"
            f"{opp.event_a['question'][:70]}\n"
            f"YES: ${opp.event_a['yes_price']:.2f} | NO: ${opp.event_a['no_price']:.2f}\n\n"
            f"📉 *СОБЫТИЕ B:*\n"
            f"{opp.event_b['question'][:70]}\n"
            f"YES: ${opp.event_b['yes_price']:.2f} | NO: ${opp.event_b['no_price']:.2f}\n\n"
        )
    
    text += (
        f"💰 *ПРОФИТ:* {opp.profit_potential:.1f}%\n\n"
        f"✅ *ЧТО ДЕЛАТЬ:*\n_{opp.action}_"
    )
    
    return text


def get_delta_list_kb(opps: List[DeltaOpportunity]) -> InlineKeyboardMarkup:
    buttons = []
    for i, opp in enumerate(opps[:5]):
        buttons.append([InlineKeyboardButton(
            f"⚠️ [{opp.topic}] {opp.profit_potential:.1f}%",
            callback_data=f"delta_view_{i}"
        )])
    buttons.append([InlineKeyboardButton("🔄 Обновить", callback_data="delta_scan")])
    buttons.append([InlineKeyboardButton("« Меню", callback_data="menu_delta")])
    return InlineKeyboardMarkup(buttons)


def get_yield_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Сканировать (95%+)", callback_data="scan_95")],
        [
            InlineKeyboardButton("🟢 Safe 97%+", callback_data="scan_97"),
            InlineKeyboardButton("🔴 Risky 90%+", callback_data="scan_90"),
        ],
        [InlineKeyboardButton("🔔 Уведомления", callback_data="alerts_menu")],
        [InlineKeyboardButton("« Назад", callback_data="menu_main")],
    ])


def get_list_kb(opps: List[dict], prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, opp in enumerate(opps[:5]):
        q = opp['question'][:25] + "..." if len(opp['question']) > 25 else opp['question']
        buttons.append([InlineKeyboardButton(
            f"{opp['risk_emoji']} {q}",
            callback_data=f"view_{prefix}_{i}"
        )])
    
    buttons.append([InlineKeyboardButton("« Меню", callback_data="menu_yield")])
    return InlineKeyboardMarkup(buttons)


def get_detail_kb(opp: dict, prefix: str, idx: int, has_ai: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    
    if not has_ai and OPENROUTER_API_KEY:
        buttons.append([InlineKeyboardButton("🧠 AI Анализ", callback_data=f"ai_{prefix}_{idx}")])
    
    buttons.append([InlineKeyboardButton("🌐 Polymarket", url=opp['url'])])
    buttons.append([InlineKeyboardButton("« К списку", callback_data=f"scan_{prefix}")])
    buttons.append([InlineKeyboardButton("« Меню", callback_data="menu_yield")])
    
    return InlineKeyboardMarkup(buttons)


# ==================== HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        format_welcome(),
        parse_mode="Markdown",
        reply_markup=get_main_kb()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # === Navigation ===
    if data == "menu_main":
        await query.message.edit_text(
            format_welcome(),
            parse_mode="Markdown",
            reply_markup=get_main_kb()
        )
    
    elif data == "menu_yield":
        await query.message.edit_text(
            format_yield_menu(),
            parse_mode="Markdown",
            reply_markup=get_yield_kb()
        )
    
    elif data == "menu_delta":
        await query.message.edit_text(
            format_delta_menu(),
            parse_mode="Markdown",
            reply_markup=get_delta_kb()
        )
    
    # === Delta Neutral ===
    elif data == "delta_scan":
        global cached_delta
        await query.message.edit_text("🔄 Сканирую логические ошибки рынка...")
        
        opps = await delta_scanner.scan()
        cached_delta = opps
        context.user_data['delta_opps'] = opps
        
        text = format_delta_list(opps)
        
        if opps:
            text += "\n👇 *Нажми для деталей:*"
            await query.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_delta_list_kb(opps)
            )
        else:
            await query.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_delta_kb()
            )
    
    elif data.startswith("delta_view_"):
        idx = int(data.split("_")[2])
        opps = context.user_data.get('delta_opps', cached_delta)
        
        if idx >= len(opps):
            await query.message.edit_text("❌ Данные устарели")
            return
        
        opp = opps[idx]
        text = format_delta_card(opp, idx + 1)
        
        # Different buttons for same vs different events
        same_event = opp.event_a['id'] == opp.event_b['id']
        
        if same_event:
            buttons = [
                [InlineKeyboardButton("🌐 Открыть на Polymarket", url=opp.event_a['url'])],
            ]
        else:
            buttons = [
                [InlineKeyboardButton("🌐 Событие A", url=opp.event_a['url'])],
                [InlineKeyboardButton("🌐 Событие B", url=opp.event_b['url'])],
            ]
        
        buttons.extend([
            [InlineKeyboardButton("« К списку", callback_data="delta_scan")],
            [InlineKeyboardButton("« Меню", callback_data="menu_delta")],
        ])
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
    
    elif data == "menu_settings":
        has_ai = "✅ Включен" if OPENROUTER_API_KEY else "❌ Нет ключа"
        await query.message.edit_text(
            f"⚙️ *НАСТРОЙКИ*\n\n"
            f"🧠 AI Анализ: {has_ai}\n\n"
            f"Для AI нужен бесплатный ключ:\n"
            f"https://openrouter.ai/keys\n\n"
            f"Установи переменную:\n"
            f"`OPENROUTER_API_KEY=твой_ключ`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="menu_main")
            ]])
        )
    
    # === Scanning ===
    elif data.startswith("scan_"):
        scan_type = data.split("_")[1]
        
        await query.message.edit_text("🔍 Сканирую рынки...")
        
        if scan_type == "97":
            min_prob = 0.97
            title = "🟢 *SAFE (97%+)*"
        elif scan_type == "90":
            min_prob = 0.90
            title = "🔴 *RISKY (90%+)*"
        else:
            min_prob = 0.95
            title = "📊 *OPPORTUNITIES (95%+)*"
        
        opps = await scanner.scan(min_prob=min_prob)
        context.user_data['opps'] = opps
        context.user_data['prefix'] = scan_type
        
        if not opps:
            await query.message.edit_text(
                f"{title}\n\n❌ Ничего не найдено",
                parse_mode="Markdown",
                reply_markup=get_yield_kb()
            )
            return
        
        text = format_list(opps, title)
        text += "\n👇 *Нажми для деталей:*"
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_list_kb(opps, scan_type)
        )
    
    # === View Detail ===
    elif data.startswith("view_"):
        parts = data.split("_")
        prefix = parts[1]
        idx = int(parts[2])
        
        opps = context.user_data.get('opps', cached_opportunities)
        if idx >= len(opps):
            await query.message.edit_text("❌ Данные устарели")
            return
        
        opp = opps[idx]
        text = format_card_basic(opp, idx + 1)
        
        ai_hint = ""
        if OPENROUTER_API_KEY:
            ai_hint = "\n\n💡 _Нажми 'AI Анализ' для умного разбора_"
        
        await query.message.edit_text(
            text + ai_hint,
            parse_mode="Markdown",
            reply_markup=get_detail_kb(opp, prefix, idx, has_ai=False),
            disable_web_page_preview=True
        )
    
    # === AI Analysis ===
    elif data.startswith("ai_"):
        parts = data.split("_")
        prefix = parts[1]
        idx = int(parts[2])
        
        opps = context.user_data.get('opps', cached_opportunities)
        if idx >= len(opps):
            await query.message.edit_text("❌ Данные устарели")
            return
        
        opp = opps[idx]
        
        await query.message.edit_text(
            f"🧠 *Анализирую с помощью AI...*\n\n"
            f"_{opp['question'][:50]}..._",
            parse_mode="Markdown"
        )
        
        # Get AI analysis
        analysis = await ai.analyze(
            question=opp['question'],
            outcome=opp['outcome'],
            price=opp['buy_price'],
            days_left=opp['days'],
            volume=opp['volume']
        )
        
        if not analysis:
            await query.message.edit_text(
                format_card_basic(opp, idx + 1) + "\n\n❌ _AI недоступен_",
                parse_mode="Markdown",
                reply_markup=get_detail_kb(opp, prefix, idx, has_ai=True),
                disable_web_page_preview=True
            )
            return
        
        # Store analysis
        opp['ai_analysis'] = analysis
        
        text = format_card_ai(opp, idx + 1, analysis)
        
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_detail_kb(opp, prefix, idx, has_ai=True),
            disable_web_page_preview=True
        )
    
    # === Alerts ===
    elif data == "alerts_menu":
        is_sub = user_id in subscribers
        status = "✅ Включены" if is_sub else "❌ Выключены"
        btn = "🔕 Выключить" if is_sub else "🔔 Включить"
        btn_data = "alerts_off" if is_sub else "alerts_on"
        
        await query.message.edit_text(
            f"🔔 *УВЕДОМЛЕНИЯ*\n\nСтатус: {status}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(btn, callback_data=btn_data)],
                [InlineKeyboardButton("« Назад", callback_data="menu_yield")],
            ])
        )
    
    elif data == "alerts_on":
        subscribers.add(user_id)
        await query.message.edit_text(
            "🔔 Уведомления включены!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="menu_yield")
            ]])
        )
    
    elif data == "alerts_off":
        subscribers.discard(user_id)
        await query.message.edit_text(
            "🔕 Уведомления выключены",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Назад", callback_data="menu_yield")
            ]])
        )


def main():
    if not BOT_TOKEN:
        print("[!] Set TELEGRAM_BOT_TOKEN")
        return
    
    if not OPENROUTER_API_KEY:
        print("[!] OPENROUTER_API_KEY not set - AI analysis disabled")
        print("[*] Get free key at: https://openrouter.ai/keys")
    else:
        print("[+] AI Analysis enabled (Llama 3.1 70B)")
    
    print("[*] Starting Nodo Bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("[+] Bot running!")
    app.run_polling()


if __name__ == "__main__":
    main()
