"""Custom actions for the Naqaha Rasa assistant."""
# Load environment variables from .env file
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()


import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Text

import requests
from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import EventType, SlotSet
from rasa_sdk.executor import CollectingDispatcher

LOGGER = logging.getLogger(__name__)

PACKAGE_DATA_PATH = Path(__file__).resolve().parent / "data" / "package_catalog.json"

SLOT_NAMES = ["selected_package", "budget", "medical_need", "preferred_city", "language_preference"]


def detect_language(text: Optional[str]) -> str:
    """Heuristic language detection between Arabic and English."""
    if not text:
        return "en"
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    return "en"


def parse_budget_value(value: Optional[str]) -> Optional[int]:
    """Extract an approximate numeric budget value from free text."""
    if not value:
        return None
    digits = re.findall(r"\d+", value.replace(",", ""))
    if not digits:
        return None
    try:
        number = int(digits[0])
    except ValueError:
        return None
    # Basic heuristic: values less than 100 likely mean thousands specified implicitly.
    if number < 100:
        number *= 1000
    return number


@dataclass
class Package:
    """Structured view of a care package entry."""

    package_id: str
    title_en: str
    title_ar: str
    description_en: str
    description_ar: str
    services_en: List[str]
    services_ar: List[str]
    focus_areas: List[str]
    cities_display: List[str]
    cities_normalized: List[str]
    price_min: int
    price_max: int

    @property
    def price_label_en(self) -> str:
        return f"SAR {self.price_min:,} – {self.price_max:,}"

    @property
    def price_label_ar(self) -> str:
        return f"{self.price_min:,} – {self.price_max:,} ريال"

    def services_for(self, language: str) -> List[str]:
        if language == "ar" and self.services_ar:
            return self.services_ar
        return self.services_en or []


class PackageKnowledgeBase:
    """Utility class for loading and querying local package knowledge."""

    def __init__(self, json_path: Path = PACKAGE_DATA_PATH) -> None:
        self.json_path = json_path
        self._packages: List[Package] = []
        self._load()

    def _load(self) -> None:
        try:
            with self.json_path.open(encoding="utf-8") as handle:
                raw_data = json.load(handle)
        except FileNotFoundError:
            LOGGER.warning("Package knowledge file not found at %s", self.json_path)
            raw_data = {"packages": []}
        except json.JSONDecodeError as exc:
            LOGGER.error("Unable to parse package knowledge base: %s", exc)
            raw_data = {"packages": []}

        packages_raw = raw_data.get("packages", raw_data)
        self._packages = [
            Package(
                package_id=item["id"],
                title_en=item["title_en"],
                title_ar=item["title_ar"],
                description_en=item["description_en"],
                description_ar=item["description_ar"],
                services_en=item.get("services_en", item.get("services", [])),
                services_ar=item.get("services_ar", []),
                focus_areas=[focus.lower() for focus in item.get("focus_areas", [])],
                cities_display=item.get("cities", []),
                cities_normalized=[city.lower() for city in item.get("cities", [])],
                price_min=int(item["price_range"]["min"]),
                price_max=int(item["price_range"]["max"]),
            )
            for item in packages_raw
        ]

    def refresh(self) -> None:
        self._load()

    def iter_packages(self) -> Iterable[Package]:
        return iter(self._packages)

    def search(
        self,
        *,
        query: Optional[str] = None,
        medical_need: Optional[str] = None,
        preferred_city: Optional[str] = None,
        budget_text: Optional[str] = None,
    ) -> List[Package]:
        """Retrieve packages ordered by a simple heuristic match score."""
        results: List[tuple[float, Package]] = []
        budget_value = parse_budget_value(budget_text)
        query_lower = (query or "").lower()
        medical_lower = (medical_need or "").lower()
        city_lower = (preferred_city or "").lower()

        for package in self._packages:
            score = 0.0

            if medical_lower:
                if any(medical_lower in focus or focus in medical_lower for focus in package.focus_areas):
                    score += 3.0

            if query_lower:
                if package.package_id in query_lower or package.title_en.lower() in query_lower:
                    score += 2.5
                elif any(term in query_lower for term in package.focus_areas):
                    score += 1.5

            if city_lower:
                if any(city_lower in city for city in package.cities_normalized):
                    score += 2.0

            if budget_value:
                if package.price_min <= budget_value <= package.price_max:
                    score += 3.0
                elif budget_value < package.price_min:
                    score += 1.0
                elif budget_value > package.price_max:
                    score += 0.5

            # Encourage packages with general relevance when no filters exist.
            if score == 0.0:
                score = 0.1

            results.append((score, package))

        results.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in results[:3]]

    def render_snippets(self, packages: List[Package], language: str) -> str:
        """Return a serialized description for the LLM prompt."""
        lines: List[str] = []
        for package in packages:
            if language == "ar":
                services = ", ".join(package.services_for(language)[:3])
                lines.append(
                    f"- {package.title_ar} ({package.price_label_ar}): {package.description_ar}. "
                    f"الخدمات: {services}. المدن: {', '.join(package.cities_display)}"
                )
            else:
                services = ", ".join(package.services_for(language)[:3])
                lines.append(
                    f"- {package.title_en} ({package.price_label_en}): {package.description_en}. "
                    f"Services: {services}. Cities: {', '.join(package.cities_display)}"
                )
        return "\n".join(lines)


class LLMClient:
    """Wrapper to interact with an external LLM endpoint."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NAQAHA_LLM_API_KEY")
        self.api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("NAQAHA_LLM_MODEL", "gpt-4o-mini")
        self.timeout = float(os.getenv("NAQAHA_LLM_TIMEOUT", "15"))

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        *,
        language: str,
        conversation_history: List[str],
        slot_context: Dict[str, Optional[str]],
        knowledge_snippet: str,
        user_message: str,
    ) -> Optional[str]:
        if not self.is_configured():
            LOGGER.info("LLM client not configured; skipping API call.")
            return None

        system_prompt = (
            "You are Naqaha's bilingual medical travel assistant. "
            "Respond empathetically, concisely, and accurately. "
            "You can speak Arabic or English; mirror the user's language. "
            "Incorporate conversation history, remembered slots, and provided knowledge. "
            "Offer helpful next steps when appropriate, but avoid hallucinating facts."
        )

        user_prompt = (
            f"User language: {'Arabic' if language == 'ar' else 'English'}\n"
            f"Conversation history:\n{os.linesep.join(conversation_history) or 'None'}\n\n"
            f"Known slots: {json.dumps(slot_context, ensure_ascii=False)}\n\n"
            f"Relevant packages:\n{knowledge_snippet or 'No matching packages found.'}\n\n"
            f"Latest user message: {user_message}\n\n"
            "Craft a helpful reply that directly addresses the request."
        )

        payload = {
            "model": self.model,
            "temperature": 0.3,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices")
            if not choices:
                LOGGER.warning("LLM API returned no choices.")
                return None
            return choices[0]["message"]["content"].strip()
        except requests.RequestException as exc:
            LOGGER.error("Failed to fetch completion from LLM: %s", exc)
            return None


class ActionSmartResponse(Action):
    """Fallback action that routes to the LLM while injecting structured context."""

    def __init__(self) -> None:
        self.knowledge_base = PackageKnowledgeBase()
        self.llm_client = LLMClient()

    def name(self) -> Text:
        return "action_smart_response"

    def _collect_history(self, tracker: Tracker, limit: int = 6) -> List[str]:
        history: List[str] = []
        for event in tracker.events:
            if event.get("event") == "user":
                text = event.get("text") or event.get("data", {}).get("text")
                if text:
                    history.append(f"User: {text}")
            elif event.get("event") == "bot":
                for message_part in event.get("data", {}).get("messages", []):
                    text = message_part.get("text")
                    if text:
                        history.append(f"Bot: {text}")
                text = event.get("text")
                if text:
                    history.append(f"Bot: {text}")
        return history[-limit:]

    def _fallback_reply(
        self,
        *,
        language: str,
        packages: List[Package],
        user_message: str,
        slot_context: Dict[str, Optional[str]],
    ) -> str:
        if not packages:
            if language == "ar":
                return "أعتذر، ما فهمت سؤالك تمامًا. هل ممكن توضح لي أكثر أو تخبرني ما الخدمة التي تبحث عنها؟"
            return "I'm sorry, I didn't catch that. Could you share a few more details about the support you need?"

        if len(packages) > 1:
            if language == "ar":
                intro = "هذه أبرز الباقات المتاحة حالياً:"
                lines = [
                    f"{idx+1}. {pkg.title_ar} ({pkg.price_label_ar})\n   • أبرز الخدمات: {', '.join(pkg.services_for(language)[:3])}"
                    for idx, pkg in enumerate(packages)
                ]
                response = intro + "\n" + "\n".join(lines)
                response += "\nاختر الباقة الأنسب أو اطلب تخصيص باقة لك."
            else:
                intro = "Here are the top packages you can consider:"
                lines = [
                    f"{idx+1}. {pkg.title_en} ({pkg.price_label_en})\n   • Key services: {', '.join(pkg.services_for(language)[:3])}"
                    for idx, pkg in enumerate(packages)
                ]
                response = intro + "\n" + "\n".join(lines)
                response += "\nLet me know which one matches you best or if you'd like a custom plan."
        else:
            package = packages[0]
            if language == "ar":
                response = (
                    f"بناءً على معلوماتك، أنصح بباقة {package.title_ar} بسعر تقريبي {package.price_label_ar}. "
                    f"تشمل خدمات مثل: {', '.join(package.services_for(language)[:3])}. "
                    "إذا احتجت تفاصيل إضافية أو تعديل الباقة خبرني."
                )
            else:
                response = (
                    f"From what I gathered, the {package.title_en} (around {package.price_label_en}) fits well. "
                    f"It covers services like {', '.join(package.services_for(language)[:3])}. "
                    "Let me know if you'd like more details or adjustments."
                )

        if slot_context.get("preferred_city"):
            city = slot_context["preferred_city"]
            if language == "ar":
                response += f" يمكننا ترتيب ذلك في مدينة {city}."
            else:
                response += f" We can coordinate that in {city}."
        return response

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        latest_message = tracker.latest_message.get("text", "")
        language = tracker.get_slot("language_preference") or detect_language(latest_message or tracker.sender_id)

        slot_context: Dict[str, Optional[str]] = {
            slot: tracker.get_slot(slot) for slot in SLOT_NAMES if tracker.get_slot(slot)
        }

        candidate_packages = self.knowledge_base.search(
            query=latest_message,
            medical_need=slot_context.get("medical_need"),
            preferred_city=slot_context.get("preferred_city"),
            budget_text=slot_context.get("budget"),
        )
        knowledge_snippet = self.knowledge_base.render_snippets(candidate_packages, language)
        history = self._collect_history(tracker)

        llm_reply = self.llm_client.generate(
            language=language,
            conversation_history=history,
            slot_context=slot_context,
            knowledge_snippet=knowledge_snippet,
            user_message=latest_message,
        )

        if llm_reply:
            dispatcher.utter_message(text=llm_reply)
        else:
            dispatcher.utter_message(
                text=self._fallback_reply(
                    language=language,
                    packages=candidate_packages,
                    user_message=latest_message,
                    slot_context=slot_context,
                )
            )

        events: List[EventType] = []
        if language != tracker.get_slot("language_preference"):
            events.append(SlotSet("language_preference", language))
        return events


class ActionRecommendPackage(Action):
    """Action that summarises a recommended package after collecting user preferences."""

    def __init__(self) -> None:
        self.knowledge_base = PackageKnowledgeBase()

    def name(self) -> Text:
        return "action_recommend_package"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        medical_need = tracker.get_slot("medical_need")
        budget = tracker.get_slot("budget")
        preferred_city = tracker.get_slot("preferred_city")
        language = tracker.get_slot("language_preference") or detect_language(tracker.latest_message.get("text"))

        matches = self.knowledge_base.search(
            medical_need=medical_need,
            preferred_city=preferred_city,
            budget_text=budget,
        )

        if matches:
            selected = matches[0]
            services_preview = ", ".join(selected.services_for(language)[:4])
            if language == "ar":
                message = (
                    f"أرشح لك باقة {selected.title_ar} بسعر تقريبي {selected.price_label_ar}. "
                    f"تضم خدمات مثل: {services_preview}. "
                    "هل ترغب أن أحجز لك موعدًا؟"
                )
            else:
                message = (
                    f"I recommend the {selected.title_en} package, priced around {selected.price_label_en}. "
                    f"It includes services like {services_preview}. "
                    "Would you like me to arrange the next steps?"
                )
            events: List[EventType] = [SlotSet("selected_package", selected.package_id)]
        else:
            if language == "ar":
                message = (
                    "ما وجدت باقة مطابقة 100٪ بناءً على التفاصيل الحالية، لكننا نستطيع تصميم باقة تناسبك. "
                    "اخبرني بالمزيد عن نوع العلاج أو المدينة المفضلة."
                )
            else:
                message = (
                    "I couldn't find an exact match with the current details, yet we can design a custom plan. "
                    "Share a little more about the treatment or city you prefer."
                )
            events = []

        dispatcher.utter_message(text=message)
        return events


class ActionResetCustomPackageSlots(Action):
    """Clear custom package slots before starting the form."""

    def name(self) -> Text:
        return "action_reset_custom_package_slots"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[EventType]:
        events: List[EventType] = [
            SlotSet("medical_need", None),
            SlotSet("budget", None),
            SlotSet("preferred_city", None),
            SlotSet("selected_package", None),
        ]
        return events


class ValidatePackageCustomForm(FormValidationAction):
    """Validation logic for the package customization form."""

    def name(self) -> Text:
        return "validate_package_custom_form"

    def validate_medical_need(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not str(slot_value).strip():
            return {"medical_need": None}
        value = str(slot_value).strip()
        LOGGER.debug("Validated medical need: %s", value)
        return {
            "medical_need": value,
            "language_preference": detect_language(value),
        }

    def validate_budget(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not str(slot_value).strip():
            return {"budget": None}
        value = str(slot_value).strip()
        LOGGER.debug("Validated budget: %s", value)
        return {
            "budget": value,
            "language_preference": detect_language(value),
        }

    def validate_preferred_city(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if not slot_value or not str(slot_value).strip():
            return {"preferred_city": None}
        value = str(slot_value).strip()
        LOGGER.debug("Validated preferred city: %s", value)
        return {
            "preferred_city": value,
            "language_preference": detect_language(value),
        }
