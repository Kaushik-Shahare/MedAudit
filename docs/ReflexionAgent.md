# Reflexion Agent Documentation

## Overview

The Reflexion Agent is a critical component in the MedAudit AI Verification system that implements the Reflexion technique for insurance claim verification. The agent improves the quality and accuracy of verification results by performing multiple iterations of reflection, critical analysis, and refinement on initial verification outputs.

## Purpose and Function

The primary purpose of the Reflexion Agent is to:

1. **Analyze and critique** initial verification results
2. **Identify potential issues** such as factual inaccuracies, overlooked information, or inconsistent reasoning
3. **Refine and improve** the verification response through iterative reflection
4. **Increase confidence scores** for decisions by validating multiple aspects of the claim
5. **Provide detailed justification** for final verification decisions

## Technical Implementation

The Reflexion Agent is implemented in `/ai_agent/core/reflexion_agent.py` and follows a multi-iteration refinement approach.

### Key Components

#### Initialization

```python
def __init__(self, max_iterations: int = 3):
    self.max_iterations = max_iterations
    try:
        if HAS_LLM_SERVICE:
            self.llm_service = LLMService()
            self.use_mock = False
        else:
            self.use_mock = True
    except Exception as e:
        logger.warning(f"Failed to initialize LLMService: {str(e)}. Using mock reflexion.")
        self.use_mock = True
```

The agent is initialized with a configurable number of maximum iterations (default: 3) and will attempt to use the LLM service if available, falling back to mock responses if needed.

#### Main Reflection Method

```python
def reflect(self, initial_prompt: str, initial_response: Dict[str, Any], 
            context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run multiple iterations of reflection to improve the verification result
    """
```

The `reflect` method takes:
- The original verification prompt
- The initial verification response
- Contextual information about the insurance claim

It then performs multiple iterations of reflection, with each iteration potentially improving the verification result.

#### Output Format

The Reflexion Agent returns a structured output:

```json
{
    "final_response": {
        "is_approved": true,
        "confidence_score": 0.92,
        "notes": "Detailed justification for the decision"
    },
    "reflections": [
        {
            "iteration": 1, 
            "reflection": "Analysis of the verification",
            "critique": "Specific issues identified"
        },
        // Additional iterations...
    ],
    "iterations": 3
}
```

## Integration with Verification Workflow

The Reflexion Agent is called during the final stage of the verification workflow in `verification_workflow.py` as part of the `finalize` method. After all other verification agents (eligibility, diagnostic, treatment, billing, and fraud) have completed their assessment, the Reflexion Agent reviews the combined results.

```python
# Apply reflexion to improve the final result
reflexion_agent = ReflexionAgent(max_iterations=3)
reflexion_result = reflexion_agent.reflect(
    initial_prompt=f"Verify insurance claim {state['insurance_form_id']}",
    initial_response=initial_result,
    context={
        "patient_data": state["patient_data"],
        "insurance_policy_data": state["insurance_policy_data"],
        "visit_data": state["visit_data"],
        "verification_results": verification_results
    }
)
```

## Fallback Mechanism

If the LLM service is unavailable or encounters an error, the Reflexion Agent uses a mock reflection system that produces increasingly confident results through each iteration. This ensures the system remains operational even when external AI services are unavailable.

```python
def _get_mock_reflection(self, current_response: Dict[str, Any], iteration: int) -> Dict[str, Any]:
    """Generate mock reflections when LLM service is unavailable"""
    # Implementation varies based on iteration number
    # Each iteration improves confidence and completeness
```

## Prompt Engineering

The Reflexion Agent uses carefully crafted prompts to guide the LLM's reflection process:

1. **System Prompt**: Sets the role and expectations for the reflection process
2. **Reflection Prompt**: Constructed dynamically to include previous reflections, context, and specific reflection instructions

### Example System Prompt

```
You are an expert AI system for reflecting on insurance claim verification results.
Your task is to critically analyze a verification response, identify any issues with it, and provide
a revised, improved response if needed.
        
Focus on accuracy, consistency with provided information, and ensuring all critical aspects of the
insurance claim are addressed (eligibility, diagnosis, treatment, billing, potential fraud).
        
Respond with a structured reflection including critique of the current response and improvements.
```

## Error Handling

The Reflexion Agent implements comprehensive error handling to ensure the verification workflow continues even if reflection fails:

1. **LLM Service Fallback**: If the LLM service is unavailable, it uses mock reflections
2. **Exception Handling**: All LLM calls are wrapped in try-except blocks
3. **Logging**: Detailed error logs help identify and debug issues

## Key Benefits

The Reflexion Agent provides several important benefits to the verification system:

1. **Improved Accuracy**: Multiple reflection iterations can catch errors or inconsistencies
2. **Higher Confidence**: Verification results have higher confidence scores after reflection
3. **Detailed Justification**: Final verification results include comprehensive justification
4. **Resilience**: Works even when external LLM services are unavailable 
5. **Adaptability**: Can focus on different aspects of verification in each iteration

## Usage Guidelines

When modifying or extending the Reflexion Agent:

1. **Maintain Error Handling**: Always keep the robust error handling in place
2. **Refine Prompts**: Prompts can be refined to improve reflection quality
3. **Tune Iterations**: The number of iterations can be adjusted based on accuracy requirements
4. **Monitor JSON Parsing**: Ensure output from LLM is properly parsed as JSON
5. **Log Reflections**: Consider storing reflections for later analysis and improvement

## Future Enhancements

Potential improvements for the Reflexion Agent include:

1. **Dynamic Iteration Control**: Adjust the number of iterations based on confidence scores
2. **Domain-Specific Reflection**: Add specialized reflection patterns for different claim types
3. **Self-evaluation Metrics**: Develop metrics to measure reflection quality
4. **Integrate Human Feedback**: Allow human feedback to guide the reflection process
5. **Reflection Memory**: Store and utilize patterns from previous successful reflections
