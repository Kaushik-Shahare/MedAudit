from typing import List, Dict, Any
import os
import logging
import json
import random
from django.conf import settings

# Try importing the generative AI packages, with fallbacks
try:
    import google.generativeai as genai
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage, SystemMessage
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    logging.warning("Google GenerativeAI package not found. Using mock LLM responses.")

logger = logging.getLogger(__name__)

class LLMService:
    """
    Service class for interacting with Google Generative AI models
    with fallback to mock responses when API is not available
    """
    def __init__(self):
        self.use_mock = not HAS_GENAI
        
        if not self.use_mock:
            try:
                api_key = os.environ.get("GOOGLE_API_KEY") or settings.GOOGLE_API_KEY
                model_name = os.environ.get("GOOGLE_MODEL_NAME") or getattr(settings, "GOOGLE_MODEL_NAME", "gemini-2.0-flash")
                
                if not api_key:
                    logger.warning("No Google API key found. Using mock LLM responses.")
                    self.use_mock = True
                    return
                    
                genai.configure(api_key=api_key)
                self.model = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=0.2,
                    convert_system_message_to_human=True,
                    google_api_key=api_key
                )
                
                # For faster, lighter queries
                flash_model = model_name if "flash" in model_name else "gemini-1.5-flash"
                self.model_flash = ChatGoogleGenerativeAI(
                    model=flash_model,
                    temperature=0.2,
                    convert_system_message_to_human=True,
                    google_api_key=api_key
                )
            except Exception as e:
                logger.warning(f"Error initializing Google Generative AI: {str(e)}. Using mock LLM responses.")
                self.use_mock = True
    
    def get_completion(self, system_prompt: str, user_prompt: str, use_flash: bool = True) -> str:
        """
        Get completion from the LLM model
        
        Args:
            system_prompt: System message to guide the model
            user_prompt: User message/query for the model
            use_flash: Whether to use the flash model (faster)
        
        Returns:
            str: Model's response
        """
        if self.use_mock:
            return self._get_mock_completion(system_prompt, user_prompt)
            
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            model_to_use = self.model_flash if use_flash else self.model
            response = model_to_use.invoke(messages)
            
            return response.content
        except Exception as e:
            logger.warning(f"Error calling LLM service: {str(e)}. Using mock response.")
            return self._get_mock_completion(system_prompt, user_prompt)
    
    def get_structured_output(self, system_prompt: str, user_prompt: str, output_schema: Dict[str, Any], use_flash: bool = True) -> Dict:
        """
        Get a structured output from the LLM according to the provided schema
        
        Args:
            system_prompt: System message to guide the model
            user_prompt: User message/query for the model
            output_schema: Schema definition for the expected output
            use_flash: Whether to use the flash model
            
        Returns:
            Dict: Structured output according to the schema
        """
        if self.use_mock:
            return self._get_mock_structured_output(output_schema)
        
        try:
            full_system_prompt = f"{system_prompt}\n\nYou must respond with a JSON object that conforms to this schema: {output_schema}"
            
            messages = [
                SystemMessage(content=full_system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            model_to_use = self.model_flash if use_flash else self.model
            response = model_to_use.invoke(messages)
            
            # Parse the response content to ensure we have a dictionary
            content = response.content
            if isinstance(content, str):
                # Try to extract JSON from the string response
                try:
                    # Look for JSON content within the response using various patterns
                    if "```json" in content:
                        # Extract JSON from code block with json tag
                        json_part = content.split("```json")[1].split("```")[0].strip()
                        parsed_content = json.loads(json_part)
                    elif "```" in content:
                        # Try other code block format (might be json without explicit tag)
                        json_part = content.split("```")[1].strip()
                        parsed_content = json.loads(json_part)
                    elif "{" in content and "}" in content:
                        # Find outermost JSON object using bracket matching
                        start = content.find("{")
                        # Simple bracket matching to find the end of the JSON object
                        count = 0
                        end = -1
                        for i in range(start, len(content)):
                            if content[i] == "{":
                                count += 1
                            elif content[i] == "}":
                                count -= 1
                                if count == 0:
                                    end = i + 1
                                    break
                                    
                        if end > start:
                            json_part = content[start:end].strip()
                            parsed_content = json.loads(json_part)
                        else:
                            # Try the whole string as a fallback
                            parsed_content = json.loads(content)
                    else:
                        # Try the whole string
                        parsed_content = json.loads(content)
                    return parsed_content
                except (json.JSONDecodeError, IndexError) as e:
                    logger.warning(f"Failed to parse JSON from LLM response: {str(e)}. Using mock response.")
                    logger.debug(f"LLM response: {content[:500]}...")
                    # One more attempt - try to fix common JSON issues
                    try:
                        # Replace single quotes with double quotes for JSON compliance
                        fixed_content = content.replace("'", "\"")
                        # Try to find anything that looks like a JSON object
                        if "{" in fixed_content and "}" in fixed_content:
                            start = fixed_content.find("{")
                            end = fixed_content.rfind("}") + 1
                            if start < end:
                                parsed_content = json.loads(fixed_content[start:end])
                                return parsed_content
                    except Exception:
                        pass
                    
                    return self._get_mock_structured_output(output_schema)
            
            # If the content is already a dict, return it directly
            if isinstance(content, dict):
                return content
                
            # Fallback to mock output if we couldn't parse the response
            logger.warning(f"Unexpected response type: {type(content)}. Using mock response.")
            return self._get_mock_structured_output(output_schema)
        except Exception as e:
            logger.warning(f"Error calling LLM service: {str(e)}. Using mock response.")
            return self._get_mock_structured_output(output_schema)
            
    def _get_mock_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Generate mock completions when LLM service is unavailable"""
        logger.info(f"Using mock LLM response for prompt: {user_prompt[:50]}...")
        
        if "eligibility" in system_prompt.lower() or "eligibility" in user_prompt.lower():
            return "The patient appears to be eligible for the insurance claim based on the policy details provided."
        elif "diagnosis" in system_prompt.lower() or "diagnosis" in user_prompt.lower():
            return "The diagnosis is supported by the medical records and is covered by the insurance policy."
        elif "treatment" in system_prompt.lower() or "treatment" in user_prompt.lower():
            return "The treatment is appropriate for the diagnosed condition and falls within policy coverage."
        elif "billing" in system_prompt.lower() or "billing" in user_prompt.lower():
            return "The billing amounts align with the treatment provided and are within reasonable cost ranges."
        elif "fraud" in system_prompt.lower() or "fraud" in user_prompt.lower():
            return "No fraud indicators detected. Claim appears to be legitimate."
        else:
            return "This is a mock response from the AI system since the LLM service is not available."
    
    def _get_mock_structured_output(self, output_schema: Dict[str, Any]) -> Dict:
        """Generate mock structured outputs when LLM service is unavailable"""
        if "is_approved" in str(output_schema):
            return {
                "is_approved": random.choice([True, True, True, False]),  # 75% approval rate
                "confidence_score": random.uniform(0.65, 0.95),
                "notes": "This is a mock verification result since the LLM service is unavailable."
            }
        elif "verification_results" in str(output_schema):
            return {
                "is_approved": True,
                "confidence_score": 0.85,
                "verification_results": {
                    "eligibility": {"is_approved": True, "confidence_score": 0.9},
                    "diagnostic": {"is_approved": True, "confidence_score": 0.85},
                    "treatment": {"is_approved": True, "confidence_score": 0.8},
                    "billing": {"is_approved": True, "confidence_score": 0.75},
                    "fraud_detection": {"is_approved": True, "confidence_score": 0.95}
                },
                "notes": "Mock verification completed successfully. This is a placeholder result."
            }
        else:
            return {"result": "Mock structured output", "confidence_score": 0.8}
