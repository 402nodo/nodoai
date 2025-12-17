"""
Smart Event Analyzer - Понимает ПОЧЕМУ событие очевидное

Анализирует:
1. Тип события (крипто, политика, спорт, даты)
2. Временные рамки
3. Текущие данные (цены крипто и тд)
4. Логическую вероятность
5. Исторический контекст
"""
import re
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class EventCategory(Enum):
    CRYPTO_PRICE = "crypto_price"
    POLITICS = "politics"
    SPORTS = "sports"
    CELEBRITY = "celebrity"
    TECH = "tech"
    ECONOMY = "economy"
    DATE_EVENT = "date_event"
    SCIENCE = "science"
    OTHER = "other"


@dataclass
class EventAnalysis:
    """Результат анализа события."""
    category: EventCategory
    confidence_score: int  # 1-100 насколько мы уверены в анализе
    predicted_outcome: str  # "YES" или "NO"
    reasons: List[str]  # Почему мы так думаем
    risks: List[str]  # Что может пойти не так
    verdict: str  # Короткий вердикт
    data_used: Dict  # Какие данные использовали


class SmartAnalyzer:
    """Умный анализатор событий."""
    
    # Ключевые слова для категоризации
    CRYPTO_KEYWORDS = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'solana', 'sol',
        'dogecoin', 'doge', 'xrp', 'cardano', 'ada', 'token', 'coin',
        'price', 'reach', 'hit', 'above', 'below', 'ath', 'all-time'
    ]
    
    POLITICS_KEYWORDS = [
        'president', 'election', 'vote', 'congress', 'senate', 'governor',
        'resign', 'impeach', 'veto', 'bill', 'law', 'minister', 'prime',
        'trump', 'biden', 'harris', 'putin', 'zelensky', 'musk', 'cabinet',
        'democrat', 'republican', 'party', 'nato', 'eu', 'un'
    ]
    
    SPORTS_KEYWORDS = [
        'win', 'championship', 'super bowl', 'nfl', 'nba', 'mlb', 'nhl',
        'world cup', 'olympics', 'finals', 'playoff', 'mvp', 'score'
    ]
    
    CELEBRITY_KEYWORDS = [
        'married', 'engaged', 'divorce', 'pregnant', 'baby', 'died', 'death',
        'kardashian', 'swift', 'bieber', 'celebrity', 'actor', 'singer'
    ]
    
    TECH_KEYWORDS = [
        'launch', 'release', 'iphone', 'apple', 'google', 'microsoft',
        'spacex', 'tesla', 'ai', 'gpt', 'openai', 'starship', 'rocket'
    ]
    
    ECONOMY_KEYWORDS = [
        'recession', 'fed', 'rate', 'inflation', 'gdp', 'unemployment',
        'stock', 'market', 'crash', 'rally', 's&p', 'dow', 'nasdaq'
    ]
    
    # Паттерны для извлечения данных
    PRICE_PATTERN = r'\$?([\d,]+(?:\.\d+)?)\s*(?:k|K|thousand|million|M|B|billion)?'
    DATE_PATTERN = r'(?:by|before|in|on)\s+(\w+\s+\d{1,2},?\s*\d{4}|\d{4}|end of \d{4})'
    
    def __init__(self):
        self.client = httpx.Client(timeout=10.0)
        self._crypto_cache = {}
        self._cache_time = None
    
    def analyze(self, question: str, current_price: float, outcome: str, days_left: int) -> EventAnalysis:
        """
        Анализирует событие и объясняет почему оно очевидное (или нет).
        
        Args:
            question: Вопрос события
            current_price: Текущая цена на рынке (0-1)
            outcome: Какой исход мы рассматриваем ("YES" или "NO")
            days_left: Сколько дней до резолюции
        """
        q_lower = question.lower()
        
        # 1. Определяем категорию
        category = self._categorize(q_lower)
        
        # 2. Анализируем в зависимости от категории
        if category == EventCategory.CRYPTO_PRICE:
            return self._analyze_crypto(question, q_lower, current_price, outcome, days_left)
        elif category == EventCategory.POLITICS:
            return self._analyze_politics(question, q_lower, current_price, outcome, days_left)
        elif category == EventCategory.TECH:
            return self._analyze_tech(question, q_lower, current_price, outcome, days_left)
        elif category == EventCategory.CELEBRITY:
            return self._analyze_celebrity(question, q_lower, current_price, outcome, days_left)
        elif category == EventCategory.ECONOMY:
            return self._analyze_economy(question, q_lower, current_price, outcome, days_left)
        else:
            return self._analyze_generic(question, q_lower, current_price, outcome, days_left, category)
    
    def _categorize(self, q_lower: str) -> EventCategory:
        """Определяет категорию события."""
        scores = {
            EventCategory.CRYPTO_PRICE: sum(1 for kw in self.CRYPTO_KEYWORDS if kw in q_lower),
            EventCategory.POLITICS: sum(1 for kw in self.POLITICS_KEYWORDS if kw in q_lower),
            EventCategory.SPORTS: sum(1 for kw in self.SPORTS_KEYWORDS if kw in q_lower),
            EventCategory.CELEBRITY: sum(1 for kw in self.CELEBRITY_KEYWORDS if kw in q_lower),
            EventCategory.TECH: sum(1 for kw in self.TECH_KEYWORDS if kw in q_lower),
            EventCategory.ECONOMY: sum(1 for kw in self.ECONOMY_KEYWORDS if kw in q_lower),
        }
        
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
        return EventCategory.OTHER
    
    def _analyze_crypto(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Анализ крипто событий."""
        reasons = []
        risks = []
        data = {}
        
        # Извлекаем целевую цену
        target_price = self._extract_price(question)
        data['target_price'] = target_price
        
        # Определяем какую крипту
        crypto = "BTC"
        if 'ethereum' in q_lower or 'eth' in q_lower:
            crypto = "ETH"
        elif 'solana' in q_lower or 'sol' in q_lower:
            crypto = "SOL"
        
        # Получаем текущую цену
        current_crypto_price = self._get_crypto_price(crypto)
        data['current_price'] = current_crypto_price
        data['crypto'] = crypto
        
        # Анализ
        if target_price and current_crypto_price:
            if 'dip' in q_lower or 'drop' in q_lower or 'below' in q_lower or 'fall' in q_lower:
                # Событие про ПАДЕНИЕ цены
                pct_drop_needed = ((current_crypto_price - target_price) / current_crypto_price) * 100
                data['change_needed'] = f"-{pct_drop_needed:.1f}%"
                
                if pct_drop_needed > 30:
                    reasons.append(f"Нужно падение на {pct_drop_needed:.0f}% за {days} дней")
                    reasons.append(f"Текущая цена ${crypto}: ${current_crypto_price:,.0f}")
                    reasons.append(f"Такие падения редки без краха рынка")
                    if days < 30:
                        reasons.append(f"Слишком мало времени ({days}д) для такого падения")
                    verdict = f"NO скорее всего - падение {pct_drop_needed:.0f}% маловероятно"
                elif pct_drop_needed > 15:
                    reasons.append(f"Нужно падение на {pct_drop_needed:.0f}%")
                    reasons.append(f"Возможно при сильной коррекции")
                    risks.append("Крипто волатильна - коррекции случаются")
                    verdict = f"Средний риск - падение {pct_drop_needed:.0f}% возможно"
                else:
                    reasons.append(f"Небольшое падение {pct_drop_needed:.0f}% вполне реально")
                    risks.append("Обычная волатильность может вызвать такое падение")
                    verdict = "Повышенный риск - такое падение вероятно"
            else:
                # Событие про РОСТ цены
                if target_price > current_crypto_price:
                    pct_growth_needed = ((target_price - current_crypto_price) / current_crypto_price) * 100
                    data['change_needed'] = f"+{pct_growth_needed:.1f}%"
                    
                    if pct_growth_needed > 100:
                        reasons.append(f"Нужен рост {pct_growth_needed:.0f}% (более чем 2x)")
                        reasons.append(f"Текущая цена: ${current_crypto_price:,.0f}")
                        reasons.append(f"За {days} дней это практически невозможно")
                        reasons.append("Исторически такие росты занимают месяцы/годы")
                        verdict = f"NO очень вероятен - рост {pct_growth_needed:.0f}% нереалистичен"
                    elif pct_growth_needed > 50:
                        reasons.append(f"Нужен рост {pct_growth_needed:.0f}%")
                        reasons.append(f"Возможно только при сильном буллране")
                        risks.append("Крипто непредсказуема, памп возможен")
                        verdict = f"NO вероятен, но {pct_growth_needed:.0f}% рост возможен"
                    elif pct_growth_needed > 20:
                        reasons.append(f"Рост {pct_growth_needed:.0f}% реалистичен для крипты")
                        risks.append("Волатильность может легко дать такой рост")
                        verdict = "Средний риск - такой рост возможен"
                    else:
                        reasons.append(f"Рост всего {pct_growth_needed:.0f}%")
                        risks.append("Легко достижимо при обычной волатильности")
                        verdict = "Высокий риск - такой рост очень вероятен"
                else:
                    reasons.append(f"Цель ${target_price:,.0f} уже достигнута!")
                    reasons.append(f"Текущая цена: ${current_crypto_price:,.0f}")
                    verdict = "YES уже сработал или сработает"
        else:
            reasons.append("Не удалось извлечь целевую цену")
            reasons.append(f"Рынок оценивает вероятность в {price*100:.0f}%")
            verdict = "Анализ ограничен - смотри на цену рынка"
        
        # Общие риски для крипты
        risks.append("Крипто-рынок очень волатилен")
        risks.append("Новости могут резко изменить цену")
        
        confidence = 70 if target_price and current_crypto_price else 40
        
        return EventAnalysis(
            category=EventCategory.CRYPTO_PRICE,
            confidence_score=confidence,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used=data
        )
    
    def _analyze_politics(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Анализ политических событий."""
        reasons = []
        risks = []
        data = {'category': 'politics', 'days_left': days}
        
        # Тип политического события
        if any(word in q_lower for word in ['resign', 'leave', 'out', 'step down']):
            # Событие про уход политика
            reasons.append("События про уход политиков редко сбываются")
            reasons.append("Политики обычно держатся за власть до последнего")
            
            if 'trump' in q_lower:
                reasons.append("Трамп известен тем что не уходит добровольно")
            elif 'putin' in q_lower:
                reasons.append("Путин у власти 20+ лет, уход маловероятен")
            elif 'biden' in q_lower:
                reasons.append("Байден уже не у власти с 2025")
                
            if days < 30:
                reasons.append(f"Всего {days} дней - слишком мало для такого события")
            
            risks.append("Внезапные скандалы могут изменить ситуацию")
            risks.append("Здоровье политика - неизвестный фактор")
            verdict = "NO вероятен - отставки редки без явных причин"
            
        elif any(word in q_lower for word in ['impeach', 'conviction', 'guilty']):
            reasons.append("Импичмент - длительный процесс")
            reasons.append("Требует политической воли обеих партий")
            if days < 60:
                reasons.append(f"За {days} дней импичмент маловероятен")
            risks.append("Политическая ситуация может резко измениться")
            verdict = "NO вероятен - импичмент редко успешен"
            
        elif any(word in q_lower for word in ['veto', 'override']):
            reasons.append("Override veto требует 2/3 голосов")
            reasons.append("Исторически override редок")
            risks.append("Зависит от конкретного законопроекта")
            verdict = "NO вероятен - override статистически редок"
            
        elif any(word in q_lower for word in ['ceasefire', 'peace', 'war end']):
            reasons.append("Мирные соглашения требуют длительных переговоров")
            reasons.append("Обычно занимают месяцы/годы")
            if 'ukraine' in q_lower or 'russia' in q_lower:
                reasons.append("Конфликт Украина-Россия продолжается 2+ года")
                reasons.append("Нет признаков скорого завершения")
            risks.append("Политика непредсказуема")
            risks.append("Внешнее давление может ускорить процесс")
            verdict = "NO вероятен - мир требует времени"
            
        elif 'election' in q_lower or 'win' in q_lower:
            reasons.append("Выборы зависят от множества факторов")
            risks.append("Опросы часто ошибаются")
            risks.append("События перед выборами могут всё изменить")
            verdict = "Зависит от конкретных кандидатов и опросов"
            
        else:
            reasons.append("Политические события часто непредсказуемы")
            reasons.append(f"Рынок оценивает вероятность в {price*100:.0f}%")
            risks.append("Политика может измениться быстро")
            verdict = f"Смотри на цену рынка: {price*100:.0f}%"
        
        confidence = 60
        
        return EventAnalysis(
            category=EventCategory.POLITICS,
            confidence_score=confidence,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used=data
        )
    
    def _analyze_tech(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Анализ tech событий."""
        reasons = []
        risks = []
        data = {'category': 'tech'}
        
        if 'spacex' in q_lower or 'starship' in q_lower:
            if 'launch' in q_lower:
                reasons.append("SpaceX имеет историю успешных запусков")
                reasons.append("Но сроки часто сдвигаются")
                risks.append("Технические проблемы могут задержать")
                verdict = "Зависит от конкретной даты и готовности"
            elif 'reusable' in q_lower or 'catch' in q_lower:
                reasons.append("Полная многоразовость - сложная задача")
                reasons.append("Требует множества успешных тестов")
                if days < 30:
                    reasons.append(f"За {days} дней маловероятно")
                verdict = "NO вероятен для сложных milestone'ов"
        
        elif 'ai' in q_lower:
            if 'agi' in q_lower or 'general' in q_lower:
                reasons.append("AGI пока не существует")
                reasons.append("Эксперты расходятся в оценках сроков")
                verdict = "NO для AGI в ближайшее время"
            else:
                reasons.append("AI развивается быстро")
                risks.append("Прорывы могут случиться неожиданно")
                verdict = "Зависит от конкретного milestone"
        
        else:
            reasons.append("Tech события зависят от множества факторов")
            reasons.append(f"Рынок оценивает: {price*100:.0f}%")
            verdict = "Смотри детали события"
        
        confidence = 50
        
        return EventAnalysis(
            category=EventCategory.TECH,
            confidence_score=confidence,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used=data
        )
    
    def _analyze_celebrity(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Анализ celebrity событий."""
        reasons = []
        risks = []
        
        if any(word in q_lower for word in ['pregnant', 'baby', 'engaged', 'married']):
            reasons.append("Личная жизнь непредсказуема")
            reasons.append("Зависит от решений конкретных людей")
            risks.append("Новости могут появиться внезапно")
            verdict = "Сложно предсказать - личные решения"
            
        elif any(word in q_lower for word in ['jail', 'prison', 'arrested']):
            reasons.append("Судебные процессы обычно длительные")
            if days < 30:
                reasons.append(f"За {days} дней тюремный срок маловероятен")
            reasons.append("Знаменитости часто избегают реального срока")
            risks.append("Но громкие дела бывают исключениями")
            verdict = "NO вероятен для короткого срока"
            
        else:
            reasons.append("Celebrity события зависят от личных решений")
            verdict = f"Рынок оценивает: {price*100:.0f}%"
        
        return EventAnalysis(
            category=EventCategory.CELEBRITY,
            confidence_score=40,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used={}
        )
    
    def _analyze_economy(self, question: str, q_lower: str, price: float, outcome: str, days: int) -> EventAnalysis:
        """Анализ экономических событий."""
        reasons = []
        risks = []
        
        if 'recession' in q_lower:
            reasons.append("Рецессия определяется постфактум")
            reasons.append("Требует 2 квартала отрицательного роста")
            reasons.append("Текущие индикаторы не показывают рецессию")
            risks.append("Экономика может измениться быстро")
            verdict = "NO вероятен если нет явных признаков"
            
        elif 'rate' in q_lower and 'fed' in q_lower:
            reasons.append("Fed публикует график заседаний")
            reasons.append("Решения зависят от данных по инфляции")
            risks.append("Fed может изменить курс при новых данных")
            verdict = "Следи за заседаниями Fed"
            
        else:
            reasons.append("Экономические события зависят от данных")
            verdict = f"Рынок оценивает: {price*100:.0f}%"
        
        return EventAnalysis(
            category=EventCategory.ECONOMY,
            confidence_score=50,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used={}
        )
    
    def _analyze_generic(self, question: str, q_lower: str, price: float, outcome: str, days: int, category: EventCategory) -> EventAnalysis:
        """Общий анализ для неопределённых событий."""
        reasons = []
        risks = []
        
        # Анализ по времени
        if days <= 7:
            reasons.append(f"Осталось всего {days} дней")
            reasons.append("За такой срок маловероятны большие изменения")
        elif days <= 14:
            reasons.append(f"До резолюции {days} дней")
            reasons.append("Краткосрочное событие")
        else:
            reasons.append(f"До резолюции {days} дней")
            reasons.append("Достаточно времени для изменений")
            risks.append("Много времени = больше неопределённости")
        
        # Анализ по цене рынка
        if price >= 0.97:
            reasons.append(f"Рынок уверен на {price*100:.0f}%")
            reasons.append("Высокая уверенность обычно обоснована")
            verdict = f"{outcome} очень вероятен ({price*100:.0f}%)"
        elif price >= 0.95:
            reasons.append(f"Рынок оценивает в {price*100:.0f}%")
            risks.append("5% шанс противоположного исхода")
            verdict = f"{outcome} вероятен, но есть риск"
        else:
            reasons.append(f"Вероятность только {price*100:.0f}%")
            risks.append("Значительный шанс другого исхода")
            verdict = "Повышенный риск!"
        
        risks.append("Всегда проверяй детали события на Polymarket")
        
        return EventAnalysis(
            category=category,
            confidence_score=45,
            predicted_outcome=outcome,
            reasons=reasons,
            risks=risks,
            verdict=verdict,
            data_used={'market_price': price, 'days': days}
        )
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Извлекает целевую цену из текста."""
        # Ищем паттерны типа $100,000 или $100K или 100000
        patterns = [
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:k|K)',  # $100K
            r'\$\s*([\d,]+(?:\.\d+)?)\s*(?:m|M)',  # $1M
            r'\$\s*([\d,]+(?:\.\d+)?)',             # $100,000
            r'([\d,]+(?:\.\d+)?)\s*(?:dollars?)',   # 100000 dollars
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                num_str = match.group(1).replace(',', '')
                num = float(num_str)
                
                # Проверяем множители
                full_match = match.group(0).lower()
                if 'k' in full_match:
                    num *= 1000
                elif 'm' in full_match:
                    num *= 1_000_000
                elif 'b' in full_match:
                    num *= 1_000_000_000
                
                return num
        
        return None
    
    def _get_crypto_price(self, symbol: str) -> Optional[float]:
        """Получает текущую цену криптовалюты."""
        try:
            # Используем CoinGecko API (бесплатный)
            ids = {'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana'}
            coin_id = ids.get(symbol, 'bitcoin')
            
            response = self.client.get(
                f"https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"}
            )
            data = response.json()
            return data[coin_id]['usd']
        except:
            # Fallback prices
            fallbacks = {'BTC': 100000, 'ETH': 3500, 'SOL': 200}
            return fallbacks.get(symbol, 100000)
    
    def close(self):
        self.client.close()


# Тест
if __name__ == "__main__":
    analyzer = SmartAnalyzer()
    
    # Тест крипто
    result = analyzer.analyze(
        "Will Bitcoin reach $200,000 by December 31, 2025?",
        current_price=0.15,
        outcome="NO",
        days_left=14
    )
    
    print(f"Category: {result.category}")
    print(f"Verdict: {result.verdict}")
    print(f"Reasons:")
    for r in result.reasons:
        print(f"  - {r}")
    print(f"Risks:")
    for r in result.risks:
        print(f"  - {r}")
    print(f"Data: {result.data_used}")

