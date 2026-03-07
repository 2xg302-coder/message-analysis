import os
from typing import List, Dict, Any, Optional, Union
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import AsyncOpenAI
from config import settings

class LLMService:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_BASE_URL
        self.model = model or settings.LLM_MODEL
        
        if not self.api_key:
            # Fallback or warning
            print("Warning: LLM API Key not configured.")
            self.client = None
        else:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def chat_completion(
        self, 
        prompt: str, 
        system_prompt: str = "You are a helpful assistant.",
        temperature: float = 0.7,
        json_mode: bool = False,
        model: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        if not self.client:
            raise ValueError("LLM Client not initialized (missing API Key)")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response_format = {"type": "json_object"} if json_mode else None
        
        try:
            response = await self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                response_format=response_format
            )
            
            content = response.choices[0].message.content
            
            if json_mode:
                return self._parse_json(content)
            
            return content
            
        except Exception as e:
            print(f"LLM Error: {e}")
            raise e

    def _parse_json(self, content: str) -> Dict[str, Any]:
        # Clean up markdown code blocks if present
        cleaned_content = content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
            
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        
        try:
            return json.loads(cleaned_content.strip())
        except json.JSONDecodeError:
            # Try to find JSON object within text
            try:
                start = cleaned_content.find('{')
                end = cleaned_content.rfind('}') + 1
                if start != -1 and end != -1:
                    return json.loads(cleaned_content[start:end])
            except:
                pass
            raise ValueError(f"Failed to parse JSON response: {content[:100]}...")

# Singleton instance
llm_service = LLMService()
