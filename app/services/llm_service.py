import logging
from typing import Optional
from groq import Groq
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """Service for interacting with Groq Cloud LLM API."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
        logger.info(f"Initialized LLMService with model: {self.model}")
    
    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
        try:
            messages = []
            
            if system_message:
                messages.append({
                    "role": "system",
                    "content": system_message
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            answer = response.choices[0].message.content
            logger.info(f"Generated response with {len(answer)} characters")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise
    
    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """
        Generate a summary of the given text.
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        prompt = f"""Please provide a concise summary of the following text in approximately {max_length} characters or less:

{text}

Summary:"""
        
        system_message = "You are a helpful assistant that creates clear, concise summaries."
        
        return self.generate_response(
            prompt=prompt,
            system_message=system_message,
            temperature=0.3,
            max_tokens=max_length // 2  # Rough token estimate
        )
    
    def extract_intent(self, query: str) -> str:
        """
        Extract intent from a user query.
        
        Args:
            query: User query
            
        Returns:
            Intent classification (question, ticket_creation, report_summary, other)
        """
        prompt = f"""Classify the following user query into one of these intents:
- question: User is asking a question
- ticket_creation: User wants to create a ticket
- report_summary: User wants to summarize a report
- other: None of the above

Query: {query}

Respond with only the intent label (question, ticket_creation, report_summary, or other):"""
        
        try:
            intent = self.generate_response(
                prompt=prompt,
                temperature=0.1,
                max_tokens=10
            ).strip().lower()
            
            # Validate intent
            valid_intents = ["question", "ticket_creation", "report_summary", "other"]
            if intent not in valid_intents:
                intent = "question"  # Default to question
            
            return intent
            
        except Exception as e:
            logger.error(f"Error extracting intent: {str(e)}")
            return "question"  # Default fallback


# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get singleton instance of LLMService."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
