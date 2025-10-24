/**
 * Enhanced Model Intelligence System
 * Provides comprehensive information about AI models including capabilities, performance, and recommendations
 */

export interface ModelInfo {
  name: string;
  displayName: string;
  description: string;
  category: 'general' | 'code' | 'chat' | 'instruct';
  recommended: boolean;
  size?: string;
  capabilities: string[];
  performance?: {
    reasoning: number;    // 1-10 scale
    coding: number;      // 1-10 scale
    speed: number;       // 1-10 scale
    efficiency: number;  // 1-10 scale
  };
  useCases: string[];
  strengths: string[];
  limitations?: string[];
}

// Comprehensive model database with detailed information
const MODEL_DATABASE: Record<string, Partial<ModelInfo>> = {
  // Qwen Models - Advanced Reasoning Champions
  'qwen3': {
    displayName: 'Qwen 3',
    description: 'Advanced multilingual model with exceptional reasoning and coding capabilities. Latest generation with improved performance.',
    category: 'general',
    recommended: true,
    capabilities: ['conversation', 'reasoning', 'analysis', 'multilingual', 'coding', 'math', 'chain-of-thought'],
    performance: { reasoning: 9, coding: 8, speed: 7, efficiency: 8 },
    useCases: ['Complex reasoning tasks', 'Multilingual conversations', 'Code analysis', 'Research assistance'],
    strengths: ['Exceptional reasoning', 'Multilingual support', 'Strong math capabilities', 'Latest architecture'],
    limitations: ['Higher resource usage', 'Slower inference for complex tasks']
  },

  'qwen2.5': {
    displayName: 'Qwen 2.5',
    description: 'Powerful multilingual model with strong instruction-following and analytical capabilities.',
    category: 'general',
    recommended: true,
    capabilities: ['conversation', 'reasoning', 'analysis', 'multilingual', 'instruction-following'],
    performance: { reasoning: 8, coding: 7, speed: 8, efficiency: 8 },
    useCases: ['General conversations', 'Analysis tasks', 'Multilingual support', 'Instruction following'],
    strengths: ['Balanced performance', 'Good multilingual support', 'Reliable instruction following'],
    limitations: ['Less specialized than newer models']
  },

  'qwen2.5vl': {
    displayName: 'Qwen 2.5 Vision',
    description: 'Vision-language model capable of understanding and analyzing images alongside text conversations.',
    category: 'general',
    recommended: true,
    capabilities: ['vision', 'image-analysis', 'multimodal', 'conversation', 'reasoning', 'visual-understanding'],
    performance: { reasoning: 8, coding: 6, speed: 6, efficiency: 7 },
    useCases: ['Image analysis', 'Visual question answering', 'Multimodal conversations', 'Document analysis'],
    strengths: ['Excellent vision capabilities', 'Multimodal understanding', 'Good reasoning with visual inputs'],
    limitations: ['Slower inference', 'Requires more resources', 'Limited to supported image formats']
  },

  'qwq': {
    displayName: 'QwQ (Qwen with Questions)',
    description: 'Reasoning-focused model designed for step-by-step problem solving with explicit questioning approach.',
    category: 'general',
    recommended: true,
    capabilities: ['reasoning', 'problem-solving', 'step-by-step', 'math', 'logic', 'critical-thinking'],
    performance: { reasoning: 10, coding: 7, speed: 6, efficiency: 7 },
    useCases: ['Complex problem solving', 'Mathematical reasoning', 'Logic puzzles', 'Research analysis'],
    strengths: ['Exceptional reasoning', 'Step-by-step approach', 'Self-questioning methodology', 'Math expertise'],
    limitations: ['Can be verbose', 'Slower for simple tasks', 'Over-analyzes simple questions']
  },

  // DeepSeek Models - Reasoning Specialists
  'deepseek-r1': {
    displayName: 'DeepSeek R1',
    description: 'Advanced reasoning model with explicit chain-of-thought capabilities and problem-solving focus.',
    category: 'general',
    recommended: true,
    capabilities: ['reasoning', 'chain-of-thought', 'problem-solving', 'math', 'analysis', 'logic'],
    performance: { reasoning: 9, coding: 8, speed: 7, efficiency: 8 },
    useCases: ['Complex reasoning', 'Mathematical problems', 'Analytical tasks', 'Research assistance'],
    strengths: ['Excellent reasoning', 'Clear thought process', 'Strong math skills', 'Problem decomposition'],
    limitations: ['Can be verbose with reasoning', 'Higher resource usage']
  },

  // Phi Models - Efficient Performance
  'phi4': {
    displayName: 'Phi-4',
    description: 'Microsoft\'s efficient model with strong performance on reasoning tasks and mathematical problems.',
    category: 'general',
    recommended: true,
    capabilities: ['reasoning', 'math', 'coding', 'efficient-inference', 'problem-solving'],
    performance: { reasoning: 8, coding: 8, speed: 9, efficiency: 9 },
    useCases: ['Quick reasoning tasks', 'Math problems', 'Code generation', 'Efficient inference'],
    strengths: ['Excellent efficiency', 'Fast inference', 'Good reasoning', 'Resource-friendly'],
    limitations: ['Smaller context window', 'Less knowledge breadth than larger models']
  },

  'phi4-reasoning': {
    displayName: 'Phi-4 Reasoning',
    description: 'Phi-4 variant specifically optimized for reasoning and problem-solving tasks with enhanced capabilities.',
    category: 'general',
    recommended: true,
    capabilities: ['reasoning', 'problem-solving', 'math', 'step-by-step', 'logic', 'analysis'],
    performance: { reasoning: 9, coding: 8, speed: 8, efficiency: 9 },
    useCases: ['Complex reasoning', 'Problem solving', 'Mathematical analysis', 'Logic tasks'],
    strengths: ['Optimized reasoning', 'Efficient performance', 'Clear problem solving', 'Fast inference'],
    limitations: ['Specialized focus', 'May over-reason simple tasks']
  },

  'phi4-mini-reasoning': {
    displayName: 'Phi-4 Mini Reasoning',
    description: 'Compact version of Phi-4 Reasoning optimized for efficiency while maintaining reasoning capabilities.',
    category: 'general',
    recommended: false,
    capabilities: ['reasoning', 'problem-solving', 'efficient-inference', 'math'],
    performance: { reasoning: 7, coding: 6, speed: 10, efficiency: 10 },
    useCases: ['Quick reasoning', 'Resource-constrained environments', 'Simple problem solving'],
    strengths: ['Very fast', 'Resource efficient', 'Good for simple reasoning'],
    limitations: ['Limited complex reasoning', 'Smaller knowledge base', 'Less capable than full versions']
  },

  'phi3': {
    displayName: 'Phi-3',
    description: 'Previous generation compact model from Microsoft with strong performance for its size.',
    category: 'general',
    recommended: false,
    capabilities: ['conversation', 'reasoning', 'efficient-inference'],
    performance: { reasoning: 6, coding: 6, speed: 9, efficiency: 9 },
    useCases: ['General conversations', 'Quick tasks', 'Resource-efficient inference'],
    strengths: ['Very efficient', 'Fast inference', 'Good for basic tasks'],
    limitations: ['Limited capabilities', 'Older architecture', 'Less powerful than newer models']
  },

  // Mistral Models - Instruction Following Masters
  'mistral-small3.1': {
    displayName: 'Mistral Small 3.1',
    description: 'Latest Mistral model optimized for instruction-following, efficiency, and balanced performance.',
    category: 'instruct',
    recommended: true,
    capabilities: ['instruction-following', 'reasoning', 'conversation', 'efficient-inference', 'structured-output'],
    performance: { reasoning: 7, coding: 7, speed: 9, efficiency: 9 },
    useCases: ['Instruction following', 'Structured tasks', 'Efficient inference', 'General conversations'],
    strengths: ['Excellent instruction following', 'Very efficient', 'Balanced performance', 'Reliable outputs'],
    limitations: ['Less reasoning depth than specialized models', 'Limited specialized knowledge']
  },

  'mistral': {
    displayName: 'Mistral 7B',
    description: 'Fast and efficient model optimized for instructions and conversational tasks.',
    category: 'instruct',
    recommended: true,
    capabilities: ['instruction-following', 'reasoning', 'conversation', 'efficient-inference'],
    performance: { reasoning: 6, coding: 6, speed: 9, efficiency: 9 },
    useCases: ['Quick instructions', 'Chat applications', 'Efficient processing', 'General tasks'],
    strengths: ['Very fast', 'Efficient', 'Good instruction following', 'Reliable'],
    limitations: ['Limited complex reasoning', 'Less specialized knowledge', 'Older architecture']
  },

  // Code Specialists
  'qwen3-coder': {
    displayName: 'Qwen 3 Coder',
    description: 'Specialized coding model with advanced programming capabilities across multiple languages.',
    category: 'code',
    recommended: true,
    capabilities: ['code-generation', 'debugging', 'code-explanation', 'multiple-languages', 'refactoring', 'code-review'],
    performance: { reasoning: 8, coding: 10, speed: 7, efficiency: 8 },
    useCases: ['Code generation', 'Debugging', 'Code reviews', 'Programming assistance', 'Refactoring'],
    strengths: ['Excellent coding abilities', 'Multiple programming languages', 'Great debugging skills', 'Code optimization'],
    limitations: ['Specialized focus', 'Less general knowledge', 'May over-engineer simple solutions']
  },

  'custom-qwen3-coder': {
    displayName: 'Custom Qwen 3 Coder',
    description: 'Customized version of Qwen 3 Coder fine-tuned for specific coding tasks and environments.',
    category: 'code',
    recommended: false,
    capabilities: ['code-generation', 'debugging', 'custom-tuned', 'specialized-tasks'],
    performance: { reasoning: 7, coding: 9, speed: 7, efficiency: 8 },
    useCases: ['Specialized coding tasks', 'Custom workflows', 'Domain-specific programming'],
    strengths: ['Custom tuning', 'Specialized capabilities', 'Optimized for specific tasks'],
    limitations: ['Limited to tuned domain', 'May lack general coding knowledge', 'Unknown performance characteristics']
  },

  'codellama': {
    displayName: 'Code Llama',
    description: 'Meta\'s specialized model for code generation and understanding with strong programming capabilities.',
    category: 'code',
    recommended: false,
    capabilities: ['code-generation', 'debugging', 'code-explanation', 'multiple-languages'],
    performance: { reasoning: 6, coding: 8, speed: 7, efficiency: 7 },
    useCases: ['Code generation', 'Programming assistance', 'Code explanation', 'Debugging'],
    strengths: ['Good coding abilities', 'Multiple languages', 'Reliable code generation'],
    limitations: ['Older architecture', 'Less advanced than newer code models', 'Limited reasoning abilities']
  },

  'devstral': {
    displayName: 'Devstral',
    description: 'Development-focused model optimized for coding tasks and software development workflows.',
    category: 'code',
    recommended: true,
    capabilities: ['code-generation', 'debugging', 'development-assistance', 'code-review', 'testing'],
    performance: { reasoning: 7, coding: 9, speed: 8, efficiency: 8 },
    useCases: ['Software development', 'Code generation', 'Development workflows', 'Testing assistance'],
    strengths: ['Development-focused', 'Good coding abilities', 'Workflow understanding', 'Testing capabilities'],
    limitations: ['Specialized focus', 'Less general knowledge', 'May be overkill for simple tasks']
  },

  // Vision Models
  'llama3.2-vision': {
    displayName: 'Llama 3.2 Vision',
    description: 'Vision-language model capable of understanding and describing images with conversational abilities.',
    category: 'general',
    recommended: false,
    capabilities: ['vision', 'image-analysis', 'multimodal', 'conversation', 'visual-understanding'],
    performance: { reasoning: 6, coding: 5, speed: 6, efficiency: 6 },
    useCases: ['Image analysis', 'Visual conversations', 'Image description', 'Multimodal tasks'],
    strengths: ['Vision capabilities', 'Multimodal understanding', 'Image analysis'],
    limitations: ['Older architecture', 'Limited reasoning', 'Slower inference', 'Less capable than newer vision models']
  },

  'llava-llama3': {
    displayName: 'LLaVA Llama 3',
    description: 'Visual instruction-tuned model for image understanding and visual question answering.',
    category: 'general',
    recommended: false,
    capabilities: ['vision', 'image-analysis', 'visual-instruction-following', 'visual-qa'],
    performance: { reasoning: 6, coding: 4, speed: 6, efficiency: 6 },
    useCases: ['Visual question answering', 'Image instruction following', 'Visual analysis'],
    strengths: ['Visual instruction following', 'Image understanding', 'Visual QA'],
    limitations: ['Limited general capabilities', 'Older architecture', 'Specialized focus only']
  },

  // Granite Models - IBM Research
  'granite4': {
    displayName: 'Granite 4',
    description: 'IBM\'s latest enterprise-grade language model with strong reasoning and code capabilities.',
    category: 'general',
    recommended: true,
    capabilities: ['conversation', 'reasoning', 'coding', 'analysis', 'enterprise-tasks', 'instruction-following'],
    performance: { reasoning: 8, coding: 8, speed: 7, efficiency: 8 },
    useCases: ['Enterprise applications', 'Code generation', 'Complex reasoning', 'Business analysis'],
    strengths: ['Enterprise focus', 'Strong coding', 'Reliable performance', 'Well-balanced'],
    limitations: ['Newer model with less community testing']
  },

  // General Purpose Models
  'llama3.3': {
    displayName: 'Llama 3.3',
    description: 'Meta\'s latest general-purpose language model with improved capabilities and performance.',
    category: 'general',
    recommended: false,
    capabilities: ['conversation', 'reasoning', 'general-knowledge', 'instruction-following'],
    performance: { reasoning: 7, coding: 6, speed: 7, efficiency: 7 },
    useCases: ['General conversations', 'Knowledge tasks', 'Reasoning', 'General assistance'],
    strengths: ['Balanced capabilities', 'Good general knowledge', 'Reliable performance'],
    limitations: ['Less specialized than newer models', 'Average performance across tasks']
  },

  'gpt-oss': {
    displayName: 'GPT-OSS',
    description: 'Open-source implementation with GPT-like capabilities for general language tasks.',
    category: 'general',
    recommended: false,
    capabilities: ['conversation', 'reasoning', 'general-knowledge', 'text-generation'],
    performance: { reasoning: 6, coding: 5, speed: 7, efficiency: 7 },
    useCases: ['General conversations', 'Text generation', 'Basic reasoning'],
    strengths: ['Open source', 'GPT-like capabilities', 'General purpose'],
    limitations: ['Less capable than commercial models', 'Limited specialized knowledge', 'Uncertain performance']
  },

  'stablelm2': {
    displayName: 'StableLM 2',
    description: 'Stability AI\'s language model with balanced performance for general tasks.',
    category: 'general',
    recommended: false,
    capabilities: ['conversation', 'reasoning', 'text-generation'],
    performance: { reasoning: 5, coding: 5, speed: 8, efficiency: 8 },
    useCases: ['General conversations', 'Text generation', 'Basic tasks'],
    strengths: ['Balanced performance', 'Efficient', 'Stable outputs'],
    limitations: ['Limited capabilities', 'Less powerful than newer models', 'Basic performance']
  },

  'openthinker': {
    displayName: 'OpenThinker',
    description: 'Model focused on reasoning and analytical thinking with strong problem-solving capabilities.',
    category: 'general',
    recommended: true,
    capabilities: ['reasoning', 'analysis', 'problem-solving', 'critical-thinking', 'analytical-tasks'],
    performance: { reasoning: 9, coding: 6, speed: 6, efficiency: 7 },
    useCases: ['Analytical tasks', 'Problem solving', 'Critical thinking', 'Research assistance'],
    strengths: ['Excellent reasoning', 'Analytical thinking', 'Problem-solving focus', 'Critical analysis'],
    limitations: ['Specialized focus', 'May be verbose', 'Less general knowledge']
  },

  'cogito': {
    displayName: 'Cogito',
    description: 'Philosophy-inspired model designed for thoughtful reasoning and deep analytical thinking.',
    category: 'general',
    recommended: true,
    capabilities: ['reasoning', 'philosophy', 'critical-thinking', 'analysis', 'thoughtful-responses'],
    performance: { reasoning: 9, coding: 5, speed: 6, efficiency: 7 },
    useCases: ['Philosophical discussions', 'Deep analysis', 'Critical thinking', 'Thoughtful reasoning'],
    strengths: ['Deep reasoning', 'Philosophical thinking', 'Thoughtful analysis', 'Critical examination'],
    limitations: ['Specialized focus', 'Less practical for coding', 'Can be overly philosophical']
  },

  'magistral': {
    displayName: 'Magistral',
    description: 'Advanced model with strong general capabilities and balanced performance across tasks.',
    category: 'general',
    recommended: true,
    capabilities: ['conversation', 'reasoning', 'instruction-following', 'analysis', 'general-tasks'],
    performance: { reasoning: 8, coding: 7, speed: 7, efficiency: 8 },
    useCases: ['General conversations', 'Instruction following', 'Reasoning tasks', 'Balanced assistance'],
    strengths: ['Balanced capabilities', 'Strong general performance', 'Reliable outputs', 'Versatile'],
    limitations: ['Less specialized than focused models', 'Average in specific domains']
  },

  // Embedding Models
  'embeddinggemma': {
    displayName: 'Embedding Gemma',
    description: 'Specialized model for generating high-quality text embeddings for semantic search.',
    category: 'general',
    recommended: false,
    capabilities: ['embeddings', 'semantic-search', 'text-similarity', 'vector-generation'],
    performance: { reasoning: 3, coding: 2, speed: 9, efficiency: 9 },
    useCases: ['Semantic search', 'Text similarity', 'Embedding generation', 'Information retrieval'],
    strengths: ['High-quality embeddings', 'Fast inference', 'Specialized purpose'],
    limitations: ['Not for conversations', 'Single purpose', 'No text generation']
  },

  'snowflake-arctic-embed2': {
    displayName: 'Arctic Embed 2',
    description: 'High-quality embedding model optimized for semantic search and retrieval tasks.',
    category: 'general',
    recommended: false,
    capabilities: ['embeddings', 'semantic-search', 'retrieval', 'similarity-matching'],
    performance: { reasoning: 3, coding: 2, speed: 9, efficiency: 9 },
    useCases: ['Information retrieval', 'Semantic search', 'Document similarity', 'RAG applications'],
    strengths: ['Excellent embeddings', 'Retrieval optimized', 'High quality vectors'],
    limitations: ['Embedding only', 'No text generation', 'Specialized purpose only']
  }
};

/**
 * Get comprehensive model information with enhanced intelligence
 */
export function getEnhancedModelInfo(modelName: string): ModelInfo {
  if (!modelName) {
    return {
      name: '',
      displayName: 'No Model Selected',
      description: 'Please select a model',
      category: 'general',
      recommended: false,
      capabilities: [],
      useCases: [],
      strengths: []
    };
  }

  // Parse model name for display and categorization
  const modelDisplayName = modelName.split(':')[0];
  const fullVersion = modelName.split(':')[1] || '';

  // Extract size from model name
  const sizeMatch = modelName.match(/(\d+[\.]?\d*[bmkMBK])/i);
  const size = sizeMatch ? sizeMatch[1].toUpperCase() : undefined;

  // Get base model info from database
  const baseModelInfo = MODEL_DATABASE[modelDisplayName] || {};

  // Determine recommendation based on various factors
  let finalRecommended = baseModelInfo.recommended || false;

  // Special logic for determining recommendations
  if (fullVersion.includes('thinking') || fullVersion.includes('reasoning') || fullVersion.includes('r1')) {
    finalRecommended = true;
  }

  // Larger models are generally more capable
  if (size && (size.includes('30B') || size.includes('32B') || size.includes('70B'))) {
    finalRecommended = true;
  }

  // Latest versions are typically better
  if (fullVersion.includes('2507') || fullVersion.includes('3.1') || fullVersion.includes('latest')) {
    finalRecommended = true;
  }

  return {
    name: modelName,
    displayName: baseModelInfo.displayName || (modelDisplayName.charAt(0).toUpperCase() + modelDisplayName.slice(1)),
    description: baseModelInfo.description || 'AI language model',
    category: baseModelInfo.category || 'general',
    recommended: finalRecommended,
    size,
    capabilities: baseModelInfo.capabilities || ['conversation'],
    performance: baseModelInfo.performance,
    useCases: baseModelInfo.useCases || ['General assistance'],
    strengths: baseModelInfo.strengths || ['AI assistance'],
    limitations: baseModelInfo.limitations
  };
}

/**
 * Get top recommended models by category
 */
export function getRecommendedModels(category?: ModelInfo['category']): string[] {
  const recommended = Object.entries(MODEL_DATABASE)
    .filter(([_, info]) => info.recommended && (!category || info.category === category))
    .sort((a, b) => (b[1].performance?.reasoning || 0) - (a[1].performance?.reasoning || 0))
    .map(([name]) => name);

  return recommended.slice(0, 5); // Top 5 recommendations
}

/**
 * Compare two models and return a comparison
 */
export function compareModels(model1: string, model2: string): {
  better: string;
  reasons: string[];
  tradeoffs: string[];
} {
  const info1 = getEnhancedModelInfo(model1);
  const info2 = getEnhancedModelInfo(model2);

  // Simple comparison logic (can be enhanced)
  const score1 = (info1.performance?.reasoning || 0) + (info1.performance?.coding || 0) + (info1.recommended ? 2 : 0);
  const score2 = (info2.performance?.reasoning || 0) + (info2.performance?.coding || 0) + (info2.recommended ? 2 : 0);

  const better = score1 > score2 ? model1 : model2;
  const betterInfo = score1 > score2 ? info1 : info2;
  const worseInfo = score1 > score2 ? info2 : info1;

  return {
    better,
    reasons: betterInfo.strengths || [],
    tradeoffs: worseInfo.strengths || []
  };
}