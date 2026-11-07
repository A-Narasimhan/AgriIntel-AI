"""
LLM Advisory Service with strict Hallucination Control.

Grounds all advisories using retrieved agricultural evidence chunks and real-time weather.
Supports configurable LLM providers (Gemini, OpenAI, Groq, or offline Grounded Synthesizer)
without hardcoding API keys or dependencies.
"""

import re
from typing import List, Optional, Tuple
import json
import httpx

from app.core.config import settings
from app.core.schemas import RetrievedChunk, WeatherContext, SourceReference
from app.rag.metadata import normalize_crop_name


class LLMService:
    """Manages prompt engineering, evidence grounding, and LLM calls."""

    @property
    def provider(self) -> str:
        """Resolve current provider dynamically from settings."""
        return (settings.llm_provider or "mock").lower()

    def build_grounded_prompt(
        self,
        query: str,
        crop: str,
        location: Optional[str],
        weather: Optional[WeatherContext],
        chunks: List[RetrievedChunk],
        crop_stage: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Build system prompt and user prompt strictly enforcing evidence citation and
        forbidding hallucination of ungrounded chemical doses or facts.
        """
        system_prompt = (
            "You are an expert Agricultural Advisory Assistant for Indian farming conditions.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Answer ONLY using the provided Agricultural Evidence Chunks and supplied Weather Context.\n"
            "2. DO NOT invent chemical doses, fertilizer quantities, or pesticide spray schedules not explicitly stated in the evidence.\n"
            "3. DO NOT invent ungrounded agricultural facts or irrigation thresholds.\n"
            "4. If the retrieved evidence does not contain sufficient information to answer the question, explicitly state: "
            "'Reliable supporting information was not found in the curated ICAR knowledge base for this query.'\n"
            "5. Cite the source document, institution, and page number for every specific recommendation made.\n"
            "6. Clearly distinguish dynamic weather observations from static agricultural best practices.\n"
            "7. Keep the advisory practical, clear, and actionable for farmers."
        )

        # Format retrieved evidence
        if chunks:
            evidence_text = "\n\n".join([
                f"[Source {i+1}: {c.title} ({c.source}), Page {c.page or 'N/A'}, "
                f"Crop: {c.crop.capitalize()}, Regional scope: {c.regional_scope or 'general'}]\n{c.text}"
                for i, c in enumerate(chunks)
            ])
        else:
            evidence_text = "NO AGRICULTURAL EVIDENCE CHUNKS RETRIEVED."

        # Format weather
        if weather and weather.is_available:
            weather_text = (
                f"Location: {weather.location}\n"
                f"Temperature: {weather.temperature}°C, Humidity: {weather.humidity}%\n"
                f"Precipitation: {weather.precipitation} mm, Wind: {weather.wind_speed} km/h\n"
                f"Condition: {weather.condition}\n"
                f"{weather.forecast_summary or ''}"
            )
        else:
            weather_text = f"Weather data unavailable ({weather.note if weather else 'No location provided'})."

        stage_info = f"\nCrop Growth Stage: {crop_stage}" if crop_stage else ""

        user_prompt = (
            f"FARMER CONTEXT:\n"
            f"- Crop: {crop.capitalize()}\n"
            f"- Location: {location or 'Not specified'}{stage_info}\n\n"
            f"REAL-TIME WEATHER CONTEXT:\n{weather_text}\n\n"
            f"RETRIEVED AGRICULTURAL EVIDENCE (CURATED SOURCES):\n"
            f"----------------------------------------\n"
            f"{evidence_text}\n"
            f"----------------------------------------\n\n"
            f"FARMER QUERY:\n\"{query}\"\n\n"
            f"Generate a structured, evidence-grounded advisory adhering strictly to the above instructions."
        )

        return system_prompt, user_prompt

   
    @staticmethod
    def _has_relevant_evidence(
        query: str,
        chunks: List[RetrievedChunk],
        intent: Optional[str] = None,
        crop: Optional[str] = None,
    ) -> bool:
        """Reject retrieved chunks that do not support the query's intent."""
        if not chunks:
            return False

        query_lower = query.lower()

        # Each group represents a different kind of evidence required.
        intent_groups = {
            "irrigation": [
                (
                    "irrigation",
                    "irrigate",
                    "water management",
                    "water requirement",
                    "watering",
                    "water stress",
                    "submergence",
                    "soil moisture",
                ),
                (
                    "critical stage",
                    "critical stages",
                    "flowering",
                    "boll formation",
                    "boll development",
                    "boll filling",
                    "water stress",
                    "moisture stress",
                    "irrigation schedule",
                    "schedule",
                    "interval",
                    "tillering",
                    "panicle",
                    "booting",
                    "tasseling",
                    "silking",
                    "pegging",
                    "pod formation",
                    "pod development",
                    "grain filling",
                    "seedling",
                    "vegetative",
                    "dry spell",
                    "drip",
                    "sprinkler",
                    "water depth",
                    "ponding",
                    "saturation",
                    "field capacity",
                    "frequency",
                ),
            ],
            "pest": [
                (
                    "pest", "pests", "insect", "insects", "bollworm", "whitefly",
                    "aphid", "thrips", "borer", "jassid", "armyworm", "caterpillar",
                    "planthopper", "bug", "mite", "weevil", "beetle", "hopper",
                    "larva", "larvae", "grub", "stem borer", "leafhopper",
                ),
                (
                    "control", "management", "monitoring", "infestation",
                    "treatment", "spray", "trap", "etl", "threshold",
                    "pheromone", "insecticide", "neem",
                ),
            ],
            "disease": [
                (
                    "disease", "diseases", "rot", "blight", "rust", "wilt",
                    "mildew", "tikka", "blast", "leaf spot", "brown spot",
                    "angular spot", "spots on leaves", "leaf curl", "mosaic",
                    "fungal", "fungus", "bacterial", "pathogen", "cercospora",
                    "anthracnose", "smut", "damping off",
                ),
                (
                    "control", "management", "symptom", "symptoms",
                    "treatment", "prevention", "spray", "fungicide",
                    "bactericide", "seed treatment",
                ),
            ],
            "nutrient_management": [
                (
                    "fertilizer", "fertiliser", "nutrient", "nutrients",
                    "urea", "npk", "dap", "potash", "nitrogen",
                    "phosphorus", "potassium", "zinc", "compost",
                    "manure", "deficiency", "micronutrient", "boron",
                ),
                (
                    "application", "deficiency", "dose",
                    "recommendation", "management", "apply",
                    "schedule", "basal", "top dressing", "kg/ha", "kg / ha",
                    "split",
                ),
            ],
            "weed": [
                (
                    "weed", "weeds", "weeding", "herbicide", "weedicide",
                    "weed management", "broadleaf",
                ),
                (
                    "control", "management", "application", "spray",
                    "pre-emergence", "post-emergence", "hoeing",
                    "interculture", "treatment", "dose", "manual",
                    "hand weeding", "kg/ha", "kg / ha",
                ),
            ],
            "cultivation": [
                (
                    "sowing", "sow", "seed rate", "spacing", "transplanting",
                    "nursery", "land preparation", "plant population",
                    "germination", "planting", "seedbed", "tillage", "ploughing",
                    "row spacing", "seed treatment", "recommended variety",
                    "recommended varieties", "hybrid variety", "cultivation",
                ),
                (
                    "cm", "kg/ha", "kg / ha", "spacing", "seed", "row",
                    "method", "depth", "recommended", "optimum",
                    "rate", "preparation", "ploughing", "tillage",
                    "seedbed", "population", "duration", "plant",
                ),
            ],
            "harvesting": [
                (
                    "harvest", "harvesting", "maturity", "ripening",
                    "picking", "storage", "post-harvest", "threshing", "thresher",
                ),
                (
                    "stage", "moisture", "signs", "time", "optimum",
                    "post-harvest", "drying", "clean", "thresher",
                    "pod", "boll", "grain", "loss", "precaution", "safe storage",
                ),
            ],
            "weather": [
                (
                    "rainfall", "rain", "temperature", "weather",
                    "forecast", "heat wave", "frost", "drought",
                    "humidity", "monsoon", "dry spell", "unseasonal",
                ),
                (
                    "advisory", "precaution", "delay", "postpone",
                    "protect", "soil moisture", "drainage", "waterlogging",
                    "irrigate", "unseasonal", "shelter", "contingency",
                    "avoid spraying", "lodging",
                ),
            ],
        }

        # Resolve intent from parameter or fallback to query keywords.
        detected_intent: Optional[str] = None
        if intent:
            clean_intent = intent.strip().lower()
            if clean_intent not in ("", "general", "none"):
                if clean_intent == "nutrient":
                    detected_intent = "nutrient_management"
                elif clean_intent in intent_groups:
                    detected_intent = clean_intent

        if not detected_intent:
            if any(term in query_lower for term in (
                "irrigation", "irrigate", "watering", "water requirement",
                "drought", "water stress", "moisture stress",
            )):
                detected_intent = "irrigation"
            elif any(term in query_lower for term in (
                "pest", "pests", "insect", "insects", "bollworm", "whitefly", "aphid", "thrips",
                "borer", "jassid", "armyworm", "caterpillar", "planthopper", "mite",
            )):
                detected_intent = "pest"
            elif any(term in query_lower for term in (
                "disease", "diseases", "rot", "blight", "rust", "wilt", "mildew", "tikka",
                "blast", "leaf curl", "leaf spot", "mosaic", "virus",
            )):
                detected_intent = "disease"
            elif any(term in query_lower for term in (
                "fertilizer", "fertiliser", "nutrient", "urea", "npk",
                "dap", "potash", "deficiency", "compost", "manure", "zinc",
            )):
                detected_intent = "nutrient_management"
            elif any(term in query_lower for term in (
                "weed", "weeds", "weeding", "herbicide", "weedicide",
            )):
                detected_intent = "weed"
            elif any(term in query_lower for term in (
                "sow", "sowing", "seed rate", "spacing", "transplanting",
                "nursery", "variety", "varieties", "land prep", "cultivation",
                "cultivate", "planting",
            )):
                detected_intent = "cultivation"
            elif any(term in query_lower for term in (
                "harvest", "harvesting", "yield", "maturity", "storage",
                "ripening", "picking",
            )):
                detected_intent = "harvesting"
            elif any(term in query_lower for term in (
                "rainfall", "rain", "temperature", "frost", "weather", "heat wave",
                "monsoon",
            )):
                detected_intent = "weather"
            else:
                # Do not claim evidence is relevant when the intent is unknown.
                return False

        groups = intent_groups[detected_intent]

        for chunk in chunks:
            if crop and normalize_crop_name(chunk.crop) != normalize_crop_name(crop):
                continue
            content = chunk.text.lower()

            # For irrigation questions, require BOTH water-management
            # evidence and a relevant stage/stress/scheduling signal in the same chunk.
            if detected_intent == "irrigation":
                water_terms = (
                    "irrigation schedule",
                    "irrigation at",
                    "irrigate at",
                    "irrigation during",
                    "water should be applied",
                    "apply irrigation",
                    "irrigations should",
                    "water requirement",
                    "water stress management",
                    "irrigation",
                    "irrigate",
                    "watering",
                    "water management",
                    "water stress",
                    "water application",
                    "submergence",
                    "soil moisture",
                )
                stage_terms = (
                    "flowering",
                    "boll formation",
                    "boll development",
                    "boll filling",
                    "critical stage",
                    "critical stages",
                    "water stress",
                    "moisture stress",
                    "irrigation schedule",
                    "schedule",
                    "interval",
                    "tillering",
                    "panicle",
                    "booting",
                    "tasseling",
                    "silking",
                    "pegging",
                    "pod formation",
                    "pod development",
                    "grain filling",
                    "seedling",
                    "vegetative",
                    "dry spell",
                    "drip",
                    "sprinkler",
                    "water depth",
                    "ponding",
                    "saturation",
                    "field capacity",
                    "frequency",
                )

                if (
                    any(term in content for term in water_terms)
                    and any(term in content for term in stage_terms)
                ):
                    return True

                continue

            if detected_intent == "disease":
                named_disease_terms = LLMService._named_disease_terms(query_lower)
                if named_disease_terms and not any(
                    term in content for term in named_disease_terms
                ):
                    continue
                continue

            if detected_intent == "pest":
                named_pest_terms = LLMService._named_pest_terms(query_lower)
                if not named_pest_terms or not any(
                    re.search(rf"\b{re.escape(term)}\b", content)
                    for term in named_pest_terms
                ):
                    continue

            if all(
                any(term in content for term in group)
                for group in groups
            ):
                return True

        if detected_intent == "disease":
            named_disease_terms = LLMService._named_disease_terms(query_lower)
            eligible_chunks = [
                chunk.text.lower()
                for chunk in chunks
                if (not crop or normalize_crop_name(chunk.crop) == normalize_crop_name(crop))
                and (
                    not named_disease_terms
                    or LLMService._matches_named_disease(chunk.text, named_disease_terms)
                )
            ]
            return bool(eligible_chunks) and LLMService._has_requested_disease_evidence(
                " ".join(eligible_chunks), query_lower
            )

        return False

    @staticmethod
    def _named_pest_terms(query: str) -> List[str]:
        pest_terms = (
            "bollworm", "whitefly", "aphid", "thrips", "jassid", "armyworm",
            "stem borer", "borer", "leafhopper", "leaf folder", "caterpillar",
            "mealybug", "mite", "weevil", "beetle", "planthopper", "hopper",
            "bug", "grub", "pink bollworm",
        )
        query_lower = query.lower()
        return [
            term for term in pest_terms
            if re.search(rf"\b{re.escape(term)}\b", query_lower)
        ]

    @staticmethod
    def _regional_scope(text: str) -> Optional[str]:
        regions = (
            "Jammu & Kashmir", "Jammu and Kashmir", "Telangana", "Andhra Pradesh",
            "Uttar Pradesh", "Uttarakhand", "Punjab", "Karnataka", "Gujarat",
            "Tamil Nadu", "Maharashtra", "Odisha", "Rajasthan", "Kerala",
            "West Bengal", "Bihar", "Chhattisgarh", "Madhya Pradesh",
        )
        for region in regions:
            if re.search(rf"\b{re.escape(region)}\b", text, re.IGNORECASE):
                return region
        return None

    @staticmethod
    def _location_regions(location: Optional[str]) -> Tuple[str, ...]:
        location_lower = (location or "").lower()
        if "warangal" in location_lower or "telangana" in location_lower:
            return ("Telangana", "Andhra Pradesh")
        if "andhra" in location_lower:
            return ("Andhra Pradesh", "Telangana")
        if "jammu" in location_lower or "kashmir" in location_lower:
            return ("Jammu & Kashmir", "Jammu and Kashmir")
        return ()

    @staticmethod
    def _has_requested_disease_evidence(content: str, query: str) -> bool:
        """Require evidence for every disease task explicitly requested."""
        query_lower = query.lower()
        aspect_terms = LLMService._requested_disease_aspect_terms(query_lower)
        return all(any(term in content for term in terms) for terms in aspect_terms)

    @staticmethod
    def _chunk_supports_disease_aspect(text: str, query: str) -> bool:
        """Keep named-disease passages that support at least one requested aspect."""
        named_disease_terms = LLMService._named_disease_terms(query)
        if named_disease_terms and not LLMService._matches_named_disease(
            text, named_disease_terms
        ):
            return False
        aspect_terms = LLMService._requested_disease_aspect_terms(query)
        content = text.lower()
        return any(any(term in content for term in terms) for terms in aspect_terms)

    @staticmethod
    def _matches_named_disease(text: str, disease_terms: List[str]) -> bool:
        """Match disease names in passage text, including tikka's leaf-spot synonym."""
        text_lower = text.lower()
        for term in disease_terms:
            if re.search(rf"\b{re.escape(term)}\b", text_lower):
                return True
            if term == "tikka" and re.search(
                r"\b(early|late|groundnut|peanut)?\s*leaf\s*spots?\b",
                text_lower,
            ):
                return True
        return False

    @staticmethod
    def _requested_disease_aspect_terms(query: str) -> List[Tuple[str, ...]]:
        """Return one evidence group for each disease task named in the query."""
        query_lower = query.lower()
        aspects: List[Tuple[str, ...]] = []
        if re.search(r"\b(symptom|symptoms|sign|signs|identify|recognize)\b", query_lower):
            aspects.append((
                "symptom", "symptoms", "sign", "signs", "lesion", "spot", "leaf",
            ))
        if re.search(
            r"\b(control|manage|management|treat|treatment|prevent|prevention|spray|fungicide|remedy)\b",
            query_lower,
        ):
            aspects.append((
                "control", "manage", "management", "treatment", "prevent",
                "spray", "fungicide", "sanitation", "seed treatment",
            ))
        if not aspects:
            aspects.append((
                "lesion", "spot", "symptom", "sign", "leaf", "panicle", "neck",
                "seedling", "fungicide", "spray", "treatment", "control",
                "management", "sanitation", "seed treatment",
            ))
        return aspects

    @staticmethod
    def _named_disease_terms(query: str) -> List[str]:
        """Extract specific disease names required for disease grounding."""
        disease_terms = (
            "blast", "tikka", "blight", "rust", "wilt", "mildew", "rot",
            "smut", "anthracnose", "cercospora", "damping off", "leaf spot",
            "brown spot", "leaf curl", "mosaic",
        )
        query_lower = query.lower()
        return [
            term for term in disease_terms
            if re.search(rf"\b{re.escape(term)}\b", query_lower)
        ]


    async def generate_advisory(
        self,
        query: str,
        crop: str,
        location: Optional[str],
        weather: Optional[WeatherContext],
        chunks: List[RetrievedChunk],
        crop_stage: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> Tuple[str, List[SourceReference], bool]:
        """
        Generate grounded advisory.
        Returns (advisory_text, sources_list, is_evidence_grounded).
        """

        if intent == "pest" and not self._named_pest_terms(query):
            advisory = (
                f"Please identify the specific {crop.capitalize()} pest you are "
                "observing, such as a named insect or symptom, so that the "
                "curated knowledge base can provide a relevant management recommendation."
            )
            return advisory, [], False

        if intent == "disease":
            relevant_chunks = [
                c for c in chunks
                if (not crop or normalize_crop_name(c.crop) == normalize_crop_name(crop))
                and self._chunk_supports_disease_aspect(c.text, query)
            ]
        else:
            relevant_chunks = [
                c for c in chunks
                if self._has_relevant_evidence(query, [c], intent=intent, crop=crop)
            ]

        preferred_regions = self._location_regions(location)
        regional_limit = False
        if preferred_regions and relevant_chunks:
            applicable = [
                c for c in relevant_chunks
                if (c.regional_scope or self._regional_scope(c.text)) is None
                or (c.regional_scope or self._regional_scope(c.text)) in preferred_regions
            ]
            if applicable:
                relevant_chunks = applicable
            else:
                relevant_chunks = []
                regional_limit = True

        if not relevant_chunks or not self._has_relevant_evidence(
            query, relevant_chunks, intent=intent, crop=crop
        ):
            if regional_limit:
                advisory = (
                    f"The curated evidence found for this {crop.capitalize()} disease "
                    f"is region-specific and does not include locally applicable "
                    f"guidance for {location}. It has not been presented as locally "
                    "validated. "
                    "Please consult your local Krishi Vigyan Kendra (KVK) or an "
                    "ICAR agricultural extension officer."
                )
                return advisory, [], False
            advisory = (
                f"Reliable supporting information was not found in the curated "
                f"knowledge base for this {crop.capitalize()} query. "
                "No agricultural recommendation has been generated. "
                "Please consult your local Krishi Vigyan Kendra (KVK) "
                "or an ICAR agricultural extension officer."
            )
            return advisory, [], False

        system_prompt, user_prompt = self.build_grounded_prompt(
            query=query,
            crop=crop,
            location=location,
            weather=weather,
            chunks=relevant_chunks,
            crop_stage=crop_stage,
        )

        # Collect source references strictly for evidence actually used
        sources: List[SourceReference] = []
        for c in relevant_chunks:
            sources.append(
                SourceReference(
                    source_id=c.source,
                    title=c.title,
                    crop=c.crop,
                    page=c.page,
                    year=c.year,
                    excerpt=c.text[:180] + "..." if len(c.text) > 180 else c.text,
                    regional_scope=c.regional_scope or self._regional_scope(c.text),
                )
            )

        # Route to appropriate provider
        if self.provider == "gemini" and settings.gemini_api_key:
            advisory = await self._call_gemini(system_prompt, user_prompt)
        elif self.provider == "openai" and settings.openai_api_key:
            advisory = await self._call_openai(system_prompt, user_prompt)
        elif self.provider == "groq" and settings.groq_api_key:
            advisory = await self._call_groq(system_prompt, user_prompt)
        else:
            # Deterministic, rule-grounded synthesis directly using relevant retrieved chunks
            advisory = self._generate_grounded_synthesis(
                query=query,
                crop=crop,
                location=location,
                weather=weather,
                chunks=relevant_chunks,
                crop_stage=crop_stage,
            )

        return advisory, sources, True

    def _generate_grounded_synthesis(
        self,
        query: str,
        crop: str,
        location: Optional[str],
        weather: Optional[WeatherContext],
        chunks: List[RetrievedChunk],
        crop_stage: Optional[str] = None,
    ) -> str:
        """
        Deterministic, offline grounded synthesis.
        Extracts salient recommendations directly from retrieved ICAR evidence chunks
        without inventing unverified information.
        """
        lines = [
            f"### Agricultural Advisory for {crop.capitalize()}",
            f"**Query**: {query}",
        ]
        if crop_stage:
            lines.append(f"**Observed Crop Growth Stage**: {crop_stage.capitalize()}")

        if weather and weather.is_available:
            lines.append(
                f"\n**Weather Advisory ({weather.location})**:\n"
                f"Current: {weather.temperature}°C, {weather.humidity}% humidity, {weather.condition}.\n"
                f"{weather.forecast_summary}"
            )
            if weather.precipitation and weather.precipitation > 2.0:
                lines.append("⚠️ *Weather Alert*: Rain detected. Postpone foliar spraying and chemical applications.")

        lines.append("\n**Curated Agricultural Recommendations**:")
        for idx, chunk in enumerate(chunks[:3], 1):
            source_citation = f"[Source: {chunk.title} ({chunk.source}), Page {chunk.page or 1}]"
            # Extract first 2-3 sentences from chunk
            text_cleaned = chunk.text.replace("\n", " ").strip()
            sentences = [s.strip() for s in text_cleaned.split(".") if len(s.strip()) > 15]
            summary_sentences = ". ".join(sentences[:3]) + "." if sentences else text_cleaned[:250] + "..."
            lines.append(f"{idx}. {summary_sentences}\n   ↳ *Citation*: {source_citation}")

        lines.append(
            "\nRecommendations below are excerpts from retrieved documents. "
            "Verify that each cited passage applies to the specific crop "
            "and question before acting on it."
        )

        return "\n".join(lines)

    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Google Gemini REST API using httpx."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                return f"Gemini API returned status {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Error contacting Gemini service: {e}"

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI-compatible endpoint using httpx."""
        base_url = settings.openai_base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                return f"OpenAI API returned status {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Error contacting OpenAI service: {e}"

    async def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Call Groq API using httpx."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                return f"Groq API returned status {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return f"Error contacting Groq service: {e}"


# Global instance
llm_service = LLMService()
