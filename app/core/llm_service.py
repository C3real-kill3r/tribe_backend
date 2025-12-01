"""
LLM Service abstraction layer supporting multiple providers.
Supports OpenAI, Anthropic (Claude), and Google Gemini.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple of (response_text, metadata_dict)
            Metadata should include 'tokens_used', 'model_used', etc.
        """
        pass


class OpenAIService(LLMService):
    """OpenAI GPT service implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        try:
            from openai import AsyncOpenAI
            # Use provided api_key, fallback to settings if not provided
            final_api_key = api_key if api_key is not None else settings.openai_api_key
            if not final_api_key:
                raise ValueError("OpenAI API key is required")
            self.client = AsyncOpenAI(api_key=final_api_key)
            self.model = model or settings.openai_model
            logger.debug(f"OpenAI service initialized with model: {self.model}")
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Generate response using OpenAI API."""
        try:
            # Prepare messages
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})
            api_messages.extend(messages)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens or 2000,
            )
            
            content = response.choices[0].message.content
            metadata = {
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "model_used": response.model,
                "provider": LLMProvider.OPENAI.value,
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"Failed to generate response from OpenAI: {str(e)}")


class AnthropicService(LLMService):
    """Anthropic Claude service implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key or settings.anthropic_api_key)
            self.model = model or settings.anthropic_model
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Generate response using Anthropic API."""
        try:
            # Anthropic uses a different message format
            # Convert messages to Anthropic format
            anthropic_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                # Anthropic uses "user" and "assistant" roles
                if role == "assistant":
                    anthropic_messages.append({"role": "assistant", "content": msg.get("content", "")})
                else:
                    anthropic_messages.append({"role": "user", "content": msg.get("content", "")})
            
            # Call Anthropic API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 2000,
                temperature=temperature,
                system=system_prompt,
                messages=anthropic_messages,
            )
            
            # Extract text content (Anthropic returns content blocks)
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text
            
            metadata = {
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens if response.usage else 0,
                "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                "completion_tokens": response.usage.output_tokens if response.usage else 0,
                "model_used": response.model,
                "provider": LLMProvider.ANTHROPIC.value,
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise Exception(f"Failed to generate response from Anthropic: {str(e)}")


class GeminiService(LLMService):
    """Google Gemini service implementation."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        try:
            import google.generativeai as genai
            api_key = api_key or settings.gemini_api_key
            if not api_key:
                raise ValueError("Gemini API key is required")
            genai.configure(api_key=api_key)
            self.model_name = model or settings.gemini_model
            self.model = genai.GenerativeModel(self.model_name)
        except ImportError:
            raise ImportError("google-generativeai package is required. Install with: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Generate response using Gemini API."""
        try:
            import asyncio
            
            # Gemini uses a chat format with history
            # Build conversation history
            chat_history = []
            for msg in messages[:-1]:  # All but the last message
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append({"role": "user", "parts": [content]})
                elif role == "assistant":
                    chat_history.append({"role": "model", "parts": [content]})
            
            # Start a chat session with history
            chat = self.model.start_chat(history=chat_history)
            
            # Get the current user message
            current_message = messages[-1].get("content", "") if messages else ""
            
            # Combine system prompt with current message if provided
            if system_prompt:
                full_message = f"{system_prompt}\n\nUser: {current_message}"
            else:
                full_message = current_message
            
            # Generate content (run in executor since Gemini SDK is sync)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: chat.send_message(
                    full_message,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens or 2000,
                    }
                )
            )
            
            content = response.text if response.text else ""
            
            # Extract token usage if available
            tokens_used = 0
            prompt_tokens = 0
            completion_tokens = 0
            
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
                completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
                tokens_used = prompt_tokens + completion_tokens
            
            metadata = {
                "tokens_used": tokens_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "model_used": self.model_name,
                "provider": LLMProvider.GEMINI.value,
            }
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise Exception(f"Failed to generate response from Gemini: {str(e)}")


def get_llm_service(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMService:
    """
    Factory function to get the appropriate LLM service.
    
    Args:
        provider: Provider name ('openai', 'anthropic', 'gemini')
                 If None, uses settings.llm_provider
        api_key: Optional API key override
        model: Optional model name override
        
    Returns:
        LLMService instance
        
    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    provider = provider or settings.llm_provider or LLMProvider.OPENAI.value
    
    # Validate API key is available
    if provider == LLMProvider.OPENAI.value:
        api_key = api_key or settings.openai_api_key
        if not api_key:
            logger.error("OpenAI API key not found. Check OPENAI_API_KEY in .env file or environment variables.")
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable in tribe_backend/.env file or "
                "configure it in settings."
            )
        logger.debug(f"Using OpenAI with model: {model or settings.openai_model}")
        return OpenAIService(api_key=api_key, model=model)
    elif provider == LLMProvider.ANTHROPIC.value:
        api_key = api_key or settings.anthropic_api_key
        if not api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or "
                "configure it in settings."
            )
        return AnthropicService(api_key=api_key, model=model)
    elif provider == LLMProvider.GEMINI.value:
        api_key = api_key or settings.gemini_api_key
        if not api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY environment variable or "
                "configure it in settings."
            )
        return GeminiService(api_key=api_key, model=model)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported: {', '.join([p.value for p in LLMProvider])}"
        )

