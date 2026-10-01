"""
LLM Advisory Service with strict Hallucination Control.

Grounds all advisories using retrieved agricultural evidence chunks and real-time weather.
Supports configurable LLM providers (Gemini, OpenAI, Groq, or offline Grounded Synthesizer)
without hardcoding API keys or dependencies.
"""

from typing import List, Optional, Tuple
import json
import httpx

from app.core.config import settings
from app.core.schemas import RetrievedChunk, WeatherContext, SourceReference


class LLMService:
    """Manages prompt engineering, evidence grounding, and LLM calls."""

    def __init__(self):
        self.provider = (settings.llm_provider or "mock").lower()

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
                f"[Source {i+1}: {c.title} ({c.source}), Page {c.page or 'N/A'}, Crop: {c.crop.capitalize()}]\n{c.text}"
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

    async def generate_advisory(
        self,
        query: str,
        crop: str,
        location: Optional[str],
        weather: Optional[WeatherContext],
        chunks: List[RetrievedChunk],
        crop_stage: Optional[str] = None,
    ) -> Tuple[str, List[SourceReference], bool]:
        """
        Generate grounded advisory.
        Returns (advisory_text, sources_list, is_evidence_grounded).
        """
        system_prompt, user_prompt = self.build_grounded_prompt(
            query=query,
            crop=crop,
            location=location,
            weather=weather,
            chunks=chunks,
            crop_stage=crop_stage,
        )

        # Collect source references
        sources: List[SourceReference] = []
        for c in chunks:
            sources.append(
                SourceReference(
                    source_id=c.source,
                    title=c.title,
                    crop=c.crop,
                    page=c.page,
                    year=c.year,
                    excerpt=c.text[:180] + "..." if len(c.text) > 180 else c.text,
                )
            )

        if not chunks:
            advisory = (
                f"No verified agricultural documents covering '{query}' for {crop.capitalize()} "
                "were found in the curated knowledge base. To prevent ungrounded advice, no recommendation "
                "is generated. Please consult your local Krishi Vigyan Kendra (KVK) or ICAR extension officer."
            )
            return advisory, [], False

        # Route to appropriate provider
        if self.provider == "gemini" and settings.gemini_api_key:
            advisory = await self._call_gemini(system_prompt, user_prompt)
        elif (self.provider == "openai" or settings.openai_api_key) and settings.openai_api_key:
            advisory = await self._call_openai(system_prompt, user_prompt)
        elif self.provider == "groq" and settings.groq_api_key:
            advisory = await self._call_groq(system_prompt, user_prompt)
        else:
            # Deterministic, rule-grounded synthesis directly using retrieved chunks
            advisory = self._generate_grounded_synthesis(query, crop, location, weather, chunks)

        return advisory, sources, True

    def _generate_grounded_synthesis(
        self,
        query: str,
        crop: str,
        location: Optional[str],
        weather: Optional[WeatherContext],
        chunks: List[RetrievedChunk],
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
            "\n**Safety & Grounding Notice**: All recommendations are strictly grounded in authoritative "
            "ICAR extension publications. Do not exceed specified dosages."
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
