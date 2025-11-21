"""
Backend Model Intelligence Utilities

Provides model information and capabilities for the email assistant.
This is a simplified backend version of the frontend model intelligence.
"""

from typing import Dict, Any, List


def getEnhancedModelInfo(model_name: str) -> Dict[str, Any]:
    """
    Get enhanced information about a model.

    Args:
        model_name: The model name (e.g., "qwen3:30b-a3b-thinking-2507-q8_0")

    Returns:
        Dict with model information
    """
    # Use the full model name for more specific matching
    full_name_lower = model_name.lower()
    base_name = model_name.split(':')[0].lower()

    # Model categories and capabilities - specific model variants
    model_info = {
        # Qwen3 variants
        'qwen3:30b': {
            'displayName': 'Qwen3 30B',
            'category': 'general',
            'recommended': True,
            'size': '30B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 9, 'coding': 8, 'speed': 6, 'efficiency': 7},
            'useCases': ['General AI tasks', 'Complex reasoning', 'Code generation'],
            'strengths': ['Excellent reasoning', 'Strong coding abilities', 'Multilingual support'],
            'limitations': ['Can be verbose', 'Requires significant compute']
        },
        'qwen3:30b-a3b-instruct-2507-q8_0': {
            'displayName': 'Qwen3 30B Instruct Q8_0',
            'category': 'general',
            'recommended': True,
            'size': '30B',
            'capabilities': ['text', 'reasoning', 'coding', 'instruction'],
            'performance': {'reasoning': 9, 'coding': 8, 'speed': 6, 'efficiency': 8},
            'useCases': ['Instruction following', 'Complex reasoning', 'Code generation'],
            'strengths': ['Excellent reasoning', 'Strong coding abilities', 'Optimized quantization'],
            'limitations': ['Can be verbose', 'Requires significant compute']
        },
        'qwen3:30b-a3b-thinking-2507-q8_0': {
            'displayName': 'Qwen3 30B Thinking Q8_0',
            'category': 'general',
            'recommended': True,
            'size': '30B',
            'capabilities': ['text', 'reasoning', 'coding', 'thinking'],
            'performance': {'reasoning': 10, 'coding': 8, 'speed': 5, 'efficiency': 8},
            'useCases': ['Deep reasoning', 'Complex problem solving', 'Advanced coding'],
            'strengths': ['Superior reasoning', 'Thinking capabilities', 'Optimized quantization'],
            'limitations': ['Slower inference', 'Requires significant compute']
        },
        'qwen3:32b': {
            'displayName': 'Qwen3 32B',
            'category': 'general',
            'recommended': True,
            'size': '32B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 9, 'coding': 8, 'speed': 6, 'efficiency': 7},
            'useCases': ['General AI tasks', 'Complex reasoning', 'Code generation'],
            'strengths': ['Excellent reasoning', 'Strong coding abilities', 'Multilingual support'],
            'limitations': ['Can be verbose', 'Requires significant compute']
        },
        'qwen3:8b': {
            'displayName': 'Qwen3 8B',
            'category': 'general',
            'recommended': True,
            'size': '8B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 7, 'speed': 8, 'efficiency': 9},
            'useCases': ['Efficient AI tasks', 'Light reasoning', 'Code assistance'],
            'strengths': ['Good balance of capabilities', 'Efficient resource usage', 'Fast inference'],
            'limitations': ['Less powerful than larger models']
        },
        'qwen3': {
            'displayName': 'Qwen3',
            'category': 'general',
            'recommended': True,
            'size': '30B+',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 9, 'coding': 8, 'speed': 6, 'efficiency': 7},
            'useCases': ['General AI tasks', 'Complex reasoning', 'Code generation'],
            'strengths': ['Excellent reasoning', 'Strong coding abilities', 'Multilingual support'],
            'limitations': ['Can be verbose', 'Requires significant compute']
        },
        'qwen2.5': {
            'displayName': 'Qwen2.5',
            'category': 'general',
            'recommended': True,
            'size': '7B-32B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 8, 'speed': 7, 'efficiency': 8},
            'useCases': ['Balanced AI tasks', 'Conversational AI', 'Light coding'],
            'strengths': ['Good balance of speed and capability', 'Efficient resource usage'],
            'limitations': ['Less powerful than larger models']
        },
        # DeepSeek R1 variants
        'deepseek-r1:1.5b': {
            'displayName': 'DeepSeek R1 1.5B',
            'category': 'general',
            'recommended': True,
            'size': '1.5B',
            'capabilities': ['text', 'reasoning', 'math'],
            'performance': {'reasoning': 8, 'coding': 6, 'speed': 9, 'efficiency': 10},
            'useCases': ['Light reasoning', 'Mathematical problems', 'Efficient AI tasks'],
            'strengths': ['Very efficient', 'Good math capabilities', 'Fast inference'],
            'limitations': ['Limited complexity handling', 'Smaller model size']
        },
        'deepseek-r1:8b': {
            'displayName': 'DeepSeek R1 8B',
            'category': 'general',
            'recommended': True,
            'size': '8B',
            'capabilities': ['text', 'reasoning', 'math', 'coding'],
            'performance': {'reasoning': 9, 'coding': 7, 'speed': 7, 'efficiency': 8},
            'useCases': ['Mathematical reasoning', 'Complex problem solving', 'Balanced tasks'],
            'strengths': ['Excellent at math and reasoning', 'Good coding abilities', 'Balanced performance'],
            'limitations': ['Moderate resource requirements']
        },
        'deepseek-r1:32b': {
            'displayName': 'DeepSeek R1 32B',
            'category': 'general',
            'recommended': True,
            'size': '32B',
            'capabilities': ['text', 'reasoning', 'math', 'coding'],
            'performance': {'reasoning': 10, 'coding': 8, 'speed': 6, 'efficiency': 7},
            'useCases': ['Advanced mathematical reasoning', 'Complex research tasks', 'Expert-level problem solving'],
            'strengths': ['Superior math and reasoning', 'Strong analytical capabilities', 'High capability'],
            'limitations': ['Slower inference', 'Higher resource requirements']
        },
        'deepseek-r1': {
            'displayName': 'DeepSeek R1',
            'category': 'general',
            'recommended': True,
            'size': '8B-32B',
            'capabilities': ['text', 'reasoning', 'math', 'coding'],
            'performance': {'reasoning': 9, 'coding': 7, 'speed': 6, 'efficiency': 7},
            'useCases': ['Mathematical reasoning', 'Complex problem solving', 'Research tasks'],
            'strengths': ['Excellent at math and reasoning', 'Strong analytical capabilities'],
            'limitations': ['Slower inference', 'Higher resource requirements']
        },
        'phi4': {
            'displayName': 'Phi-4',
            'category': 'general',
            'recommended': True,
            'size': '14B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 9, 'speed': 8, 'efficiency': 9},
            'useCases': ['Code generation', 'Technical writing', 'Efficient AI tasks'],
            'strengths': ['Excellent coding performance', 'Very efficient', 'Good reasoning'],
            'limitations': ['Smaller context window']
        },
        'mistral-small3.1': {
            'displayName': 'Mistral Small 3.1',
            'category': 'general',
            'recommended': True,
            'size': '24B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 7, 'speed': 7, 'efficiency': 8},
            'useCases': ['Balanced conversational AI', 'Light coding tasks'],
            'strengths': ['Good balance of capabilities', 'Efficient for its size'],
            'limitations': ['Not the most powerful model available']
        },
        'codellama': {
            'displayName': 'CodeLlama',
            'category': 'code',
            'recommended': False,
            'size': '7B-34B',
            'capabilities': ['coding', 'text'],
            'performance': {'reasoning': 6, 'coding': 9, 'speed': 7, 'efficiency': 7},
            'useCases': ['Code generation', 'Code explanation', 'Technical documentation'],
            'strengths': ['Specialized for coding tasks', 'Good code understanding'],
            'limitations': ['Less capable at general reasoning', 'Older model architecture']
        },
        'llama3.3': {
            'displayName': 'Llama 3.3',
            'category': 'general',
            'recommended': False,
            'size': '70B',
            'capabilities': ['text', 'reasoning'],
            'performance': {'reasoning': 7, 'coding': 6, 'speed': 5, 'efficiency': 6},
            'useCases': ['General text generation', 'Basic reasoning tasks'],
            'strengths': ['Large model size', 'Good general capabilities'],
            'limitations': ['Slower inference', 'High resource requirements', 'Less specialized']
        },
        'granite4': {
            'displayName': 'Granite 4',
            'category': 'general',
            'recommended': True,
            'size': '3B-10B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 7, 'coding': 7, 'speed': 8, 'efficiency': 9},
            'useCases': ['Efficient AI tasks', 'Enterprise applications', 'Balanced workloads'],
            'strengths': ['Very efficient', 'Good enterprise features', 'Balanced performance'],
            'limitations': ['Smaller model size limits maximum capability']
        },
        'openthinker': {
            'displayName': 'OpenThinker',
            'category': 'general',
            'recommended': True,
            'size': '32B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 7, 'speed': 6, 'efficiency': 7},
            'useCases': ['Research and analysis', 'Complex reasoning', 'Technical tasks'],
            'strengths': ['Strong reasoning capabilities', 'Good at analytical tasks'],
            'limitations': ['Newer model, less proven track record']
        },
        'cogito': {
            'displayName': 'Cogito',
            'category': 'general',
            'recommended': True,
            'size': '32B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 7, 'speed': 6, 'efficiency': 7},
            'useCases': ['Philosophical reasoning', 'Ethical AI tasks', 'Complex analysis'],
            'strengths': ['Unique reasoning approach', 'Good at nuanced topics'],
            'limitations': ['Specialized focus may not suit all tasks']
        },
        'magistral': {
            'displayName': 'Magistral',
            'category': 'general',
            'recommended': True,
            'size': '24B',
            'capabilities': ['text', 'reasoning', 'coding'],
            'performance': {'reasoning': 8, 'coding': 7, 'speed': 7, 'efficiency': 8},
            'useCases': ['Balanced AI applications', 'Content creation', 'Analysis tasks'],
            'strengths': ['Good all-around performance', 'Balanced capabilities'],
            'limitations': ['Not specialized for any particular domain']
        }
    }

    # Try to get specific model info first, then fall back to base name
    base_info = model_info.get(full_name_lower, model_info.get(base_name, {
        'displayName': model_name.split(':')[0].title(),
        'category': 'general',
        'recommended': False,
        'size': 'Unknown',
        'capabilities': ['text'],
        'performance': {'reasoning': 5, 'coding': 5, 'speed': 5, 'efficiency': 5},
        'useCases': ['General AI tasks'],
        'strengths': ['Basic AI capabilities'],
        'limitations': ['Limited information available']
    }))

    # Add description based on category and capabilities
    if base_info['category'] == 'code':
        base_info['description'] = f"Specialized coding model with strong programming capabilities. {base_info['size']} parameters."
    elif base_info['recommended']:
        base_info['description'] = f"High-quality general-purpose AI model recommended for most tasks. {base_info['size']} parameters with excellent {', '.join(base_info['capabilities'])} capabilities."
    else:
        base_info['description'] = f"General-purpose AI model suitable for basic tasks. {base_info['size']} parameters."

    return base_info


def getModelCategory(model_name: str) -> str:
    """Get the category of a model."""
    info = getEnhancedModelInfo(model_name)
    return info.get('category', 'general')


def isRecommendedModel(model_name: str) -> bool:
    """Check if a model is recommended."""
    info = getEnhancedModelInfo(model_name)
    return info.get('recommended', False)


def getModelCapabilities(model_name: str) -> List[str]:
    """Get the capabilities of a model."""
    info = getEnhancedModelInfo(model_name)
    return info.get('capabilities', ['text'])