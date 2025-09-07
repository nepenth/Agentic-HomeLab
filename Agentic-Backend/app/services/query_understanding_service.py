"""
Query Understanding and Expansion Service.

This service provides intelligent query parsing, expansion, and understanding
to improve search relevance and user experience.
"""

import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter

from app.services.ollama_client import OllamaClient
from app.services.semantic_processing import embedding_service
from app.utils.logging import get_logger

logger = get_logger("query_understanding_service")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class QueryType(Enum):
    """Types of queries that can be identified."""
    FACTUAL = "factual"  # "What is machine learning?"
    NAVIGATIONAL = "navigational"  # "Go to settings"
    TRANSACTIONAL = "transactional"  # "Download PDF"
    CONVERSATIONAL = "conversational"  # "Tell me about..."
    COMPARATIVE = "comparative"  # "Compare X vs Y"
    EXPLORATORY = "exploratory"  # "How does X work?"
    AMBIGUOUS = "ambiguous"  # Unclear intent


class QueryIntent(Enum):
    """Specific intents that can be detected."""
    SEARCH = "search"
    EXPLORE = "explore"
    COMPARE = "compare"
    SUMMARIZE = "summarize"
    ANALYZE = "analyze"
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    NAVIGATE = "navigate"


@dataclass
class QueryAnalysis:
    """Analysis result of a user query."""
    original_query: str
    cleaned_query: str
    query_type: QueryType
    intent: QueryIntent
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    sentiment: str = "neutral"  # positive, negative, neutral
    complexity: str = "simple"  # simple, moderate, complex
    confidence_score: float = 0.0
    suggested_expansions: List[str] = field(default_factory=list)
    related_queries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryExpansion:
    """Expanded query with additional context."""
    original_query: str
    expanded_query: str
    expansion_type: str  # synonym, related, contextual, temporal
    confidence_score: float
    reasoning: str


class QueryUnderstandingService:
    """Service for understanding and expanding user queries."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.ollama_client = ollama_client or OllamaClient()
        self.stop_words = set(stopwords.words('english'))

        # Query pattern recognition
        self.query_patterns = {
            QueryType.FACTUAL: [
                r'^what is', r'^who is', r'^when (was|did)', r'^where is',
                r'^how (much|many|long|old)', r'^why (does|do|did)'
            ],
            QueryType.NAVIGATIONAL: [
                r'^go to', r'^navigate to', r'^show me', r'^open',
                r'^find', r'^locate'
            ],
            QueryType.TRANSACTIONAL: [
                r'^download', r'^upload', r'^create', r'^delete',
                r'^update', r'^save', r'^send'
            ],
            QueryType.CONVERSATIONAL: [
                r'^tell me', r'^explain', r'^describe', r'^help me'
            ],
            QueryType.COMPARATIVE: [
                r' vs ', r' versus ', r' compare ', r' difference '
            ],
            QueryType.EXPLORATORY: [
                r'^how (does|do|can|should)', r'^what are the',
                r'^can you', r'^is there'
            ]
        }

        # Intent keywords
        self.intent_keywords = {
            QueryIntent.SEARCH: ['find', 'search', 'look for', 'get'],
            QueryIntent.EXPLORE: ['explore', 'discover', 'learn about', 'understand'],
            QueryIntent.COMPARE: ['compare', 'vs', 'versus', 'difference', 'better'],
            QueryIntent.SUMMARIZE: ['summarize', 'summary', 'overview', 'brief'],
            QueryIntent.ANALYZE: ['analyze', 'analysis', 'examine', 'review'],
            QueryIntent.CREATE: ['create', 'make', 'build', 'generate'],
            QueryIntent.MODIFY: ['edit', 'update', 'change', 'modify'],
            QueryIntent.DELETE: ['delete', 'remove', 'erase', 'clear'],
            QueryIntent.NAVIGATE: ['go to', 'navigate', 'show', 'display']
        }

    async def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze a user query to understand intent, type, and context.

        Args:
            query: The user's search query

        Returns:
            QueryAnalysis with detailed understanding
        """
        start_time = datetime.now()

        try:
            # Clean and preprocess query
            cleaned_query = self._clean_query(query)

            # Determine query type
            query_type = self._classify_query_type(cleaned_query)

            # Determine intent
            intent = self._classify_intent(cleaned_query)

            # Extract entities and keywords
            entities = self._extract_entities(cleaned_query)
            keywords = self._extract_keywords(cleaned_query)

            # Detect topics
            topics = await self._detect_topics(cleaned_query)

            # Analyze sentiment
            sentiment = self._analyze_sentiment(cleaned_query)

            # Assess complexity
            complexity = self._assess_complexity(cleaned_query)

            # Generate expansions
            suggested_expansions = await self._generate_expansions(cleaned_query, query_type)

            # Generate related queries
            related_queries = self._generate_related_queries(cleaned_query, topics)

            # Calculate confidence
            confidence_score = self._calculate_confidence(
                query_type, intent, entities, keywords
            )

            analysis = QueryAnalysis(
                original_query=query,
                cleaned_query=cleaned_query,
                query_type=query_type,
                intent=intent,
                entities=entities,
                keywords=keywords,
                topics=topics,
                sentiment=sentiment,
                complexity=complexity,
                confidence_score=confidence_score,
                suggested_expansions=suggested_expansions,
                related_queries=related_queries,
                metadata={
                    'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'query_length': len(query),
                    'word_count': len(cleaned_query.split())
                }
            )

            logger.info(f"Query analysis completed: {query_type.value} intent with {confidence_score:.2f} confidence")
            return analysis

        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            # Return basic analysis on error
            return QueryAnalysis(
                original_query=query,
                cleaned_query=query,
                query_type=QueryType.AMBIGUOUS,
                intent=QueryIntent.SEARCH,
                confidence_score=0.0
            )

    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query text."""
        # Convert to lowercase
        cleaned = query.lower().strip()

        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Remove special characters but keep spaces and alphanumeric
        cleaned = re.sub(r'[^\w\s]', '', cleaned)

        # Remove common filler words
        filler_words = ['please', 'can you', 'could you', 'would you', 'i want to']
        for filler in filler_words:
            cleaned = cleaned.replace(filler, '')

        return cleaned.strip()

    def _classify_query_type(self, query: str) -> QueryType:
        """Classify the type of query based on patterns."""
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return query_type

        # Default to conversational if no pattern matches
        return QueryType.CONVERSATIONAL

    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify the intent of the query."""
        query_lower = query.lower()

        # Count keyword matches for each intent
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            intent_scores[intent] = score

        # Return intent with highest score
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            if intent_scores[best_intent] > 0:
                return best_intent

        # Default to search
        return QueryIntent.SEARCH

    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from the query."""
        # Simple entity extraction (can be enhanced with NER models)
        entities = []

        # Look for capitalized words (potential proper nouns)
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1:
                entities.append(word)

        # Look for common entity patterns
        # Organizations, products, etc.
        entity_patterns = [
            r'\b[A-Z][a-z]+ (Inc|Ltd|Corp|LLC|Company)\b',  # Company names
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Person names
            r'\b\d{4}\b',  # Years
        ]

        for pattern in entity_patterns:
            matches = re.findall(pattern, query)
            entities.extend(matches)

        return list(set(entities))  # Remove duplicates

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query."""
        try:
            # Tokenize and remove stop words
            tokens = word_tokenize(query)
            keywords = [
                word for word in tokens
                if word.lower() not in self.stop_words
                and len(word) > 2
                and word.isalnum()
            ]

            # Get most common keywords
            keyword_counts = Counter(keywords)
            top_keywords = [word for word, _ in keyword_counts.most_common(10)]

            return top_keywords

        except Exception:
            # Fallback to simple split
            words = query.split()
            return [word for word in words if len(word) > 2][:10]

    async def _detect_topics(self, query: str) -> List[str]:
        """Detect topics/categories in the query."""
        # Simple topic detection based on keywords
        topic_keywords = {
            'technology': ['computer', 'software', 'hardware', 'programming', 'code', 'algorithm'],
            'science': ['research', 'study', 'experiment', 'theory', 'physics', 'chemistry'],
            'business': ['company', 'market', 'finance', 'investment', 'strategy', 'management'],
            'health': ['medical', 'disease', 'treatment', 'health', 'medicine', 'doctor'],
            'education': ['learn', 'study', 'course', 'school', 'university', 'education'],
            'entertainment': ['movie', 'music', 'game', 'book', 'film', 'entertainment']
        }

        detected_topics = []
        query_lower = query.lower()

        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_topics.append(topic)

        # If no topics detected, try AI-based topic detection
        if not detected_topics:
            try:
                detected_topics = await self._ai_topic_detection(query)
            except Exception:
                pass

        return detected_topics[:3]  # Limit to top 3 topics

    async def _ai_topic_detection(self, query: str) -> List[str]:
        """Use AI to detect topics in the query."""
        try:
            prompt = f"""
            Analyze this query and identify the main topics/categories it relates to.
            Query: "{query}"

            Return only a comma-separated list of topics (max 3):
            """

            async with self.ollama_client:
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    model="llama2",
                    max_tokens=50,
                    temperature=0.1
                )

            topics_text = response.get('response', '').strip()
            topics = [t.strip() for t in topics_text.split(',') if t.strip()]

            return topics[:3]

        except Exception:
            return []

    def _analyze_sentiment(self, query: str) -> str:
        """Analyze the sentiment of the query."""
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'best', 'love']
        negative_words = ['bad', 'terrible', 'awful', 'worst', 'hate', 'dislike', 'poor']

        query_lower = query.lower()
        positive_count = sum(1 for word in positive_words if word in query_lower)
        negative_count = sum(1 for word in negative_words if word in query_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _assess_complexity(self, query: str) -> str:
        """Assess the complexity of the query."""
        word_count = len(query.split())

        if word_count <= 3:
            return "simple"
        elif word_count <= 8:
            return "moderate"
        else:
            return "complex"

    async def _generate_expansions(self, query: str, query_type: QueryType) -> List[str]:
        """Generate suggested query expansions."""
        expansions = []

        # Basic expansions based on query type
        if query_type == QueryType.FACTUAL:
            expansions.extend([
                f"what is {query} in detail",
                f"explain {query} simply",
                f"{query} examples"
            ])
        elif query_type == QueryType.CONVERSATIONAL:
            expansions.extend([
                f"{query} in detail",
                f"tell me more about {query}",
                f"{query} examples and use cases"
            ])

        # AI-based expansions
        try:
            ai_expansions = await self._ai_query_expansion(query)
            expansions.extend(ai_expansions)
        except Exception:
            pass

        return expansions[:5]  # Limit to 5 expansions

    async def _ai_query_expansion(self, query: str) -> List[str]:
        """Use AI to generate query expansions."""
        try:
            prompt = f"""
            Given this search query: "{query}"

            Generate 3 alternative or expanded versions of this query that would help find more relevant results.
            Make them concise and natural.

            Return only the 3 queries, one per line:
            """

            async with self.ollama_client:
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    model="llama2",
                    max_tokens=100,
                    temperature=0.3
                )

            expansions_text = response.get('response', '')
            expansions = [
                line.strip() for line in expansions_text.split('\n')
                if line.strip() and not line.startswith(('Query:', 'Return:'))
            ]

            return expansions[:3]

        except Exception:
            return []

    def _generate_related_queries(self, query: str, topics: List[str]) -> List[str]:
        """Generate related queries based on topics."""
        related_queries = []

        # Topic-based related queries
        for topic in topics:
            related_queries.extend([
                f"{topic} basics",
                f"latest in {topic}",
                f"{topic} trends"
            ])

        # Query-based variations
        words = query.split()
        if len(words) > 1:
            # Remove one word at a time
            for i in range(len(words)):
                variation = ' '.join(words[:i] + words[i+1:])
                if variation != query:
                    related_queries.append(variation)

        return related_queries[:5]

    def _calculate_confidence(self, query_type: QueryType, intent: QueryIntent,
                            entities: List[str], keywords: List[str]) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.5  # Base confidence

        # Higher confidence if we found entities
        if entities:
            confidence += 0.2

        # Higher confidence if we found keywords
        if keywords:
            confidence += 0.1

        # Higher confidence for clear query types
        if query_type != QueryType.AMBIGUOUS:
            confidence += 0.2

        return min(1.0, confidence)

    async def expand_query(self, query: str, expansion_type: str = "auto") -> QueryExpansion:
        """
        Expand a query with additional context or related terms.

        Args:
            query: Original query to expand
            expansion_type: Type of expansion (auto, synonym, related, contextual)

        Returns:
            QueryExpansion with expanded query
        """
        try:
            if expansion_type == "auto":
                # Analyze query first to determine best expansion
                analysis = await self.analyze_query(query)
                expansion_type = self._choose_expansion_type(analysis)

            if expansion_type == "synonym":
                expanded = await self._expand_with_synonyms(query)
            elif expansion_type == "related":
                expanded = await self._expand_with_related_terms(query)
            elif expansion_type == "contextual":
                expanded = await self._expand_with_context(query)
            else:
                expanded = query

            confidence = 0.8 if expanded != query else 0.5

            return QueryExpansion(
                original_query=query,
                expanded_query=expanded,
                expansion_type=expansion_type,
                confidence_score=confidence,
                reasoning=f"Expanded using {expansion_type} approach"
            )

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return QueryExpansion(
                original_query=query,
                expanded_query=query,
                expansion_type="none",
                confidence_score=0.0,
                reasoning="Expansion failed, returning original query"
            )

    def _choose_expansion_type(self, analysis: QueryAnalysis) -> str:
        """Choose the best expansion type based on analysis."""
        if analysis.complexity == "simple":
            return "synonym"
        elif analysis.query_type == QueryType.EXPLORATORY:
            return "contextual"
        else:
            return "related"

    async def _expand_with_synonyms(self, query: str) -> str:
        """Expand query with synonyms."""
        try:
            prompt = f"""
            Given this query: "{query}"

            Provide synonyms or related terms for the main concepts.
            Return an expanded version of the query using these synonyms.

            Expanded query:
            """

            async with self.ollama_client:
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    model="llama2",
                    max_tokens=50,
                    temperature=0.2
                )

            expanded = response.get('response', '').strip()
            return expanded if expanded else query

        except Exception:
            return query

    async def _expand_with_related_terms(self, query: str) -> str:
        """Expand query with related terms."""
        try:
            prompt = f"""
            Given this query: "{query}"

            Add related terms and concepts to make the query more comprehensive.
            Return an expanded version that would find more relevant results.

            Expanded query:
            """

            async with self.ollama_client:
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    model="llama2",
                    max_tokens=50,
                    temperature=0.2
                )

            expanded = response.get('response', '').strip()
            return expanded if expanded else query

        except Exception:
            return query

    async def _expand_with_context(self, query: str) -> str:
        """Expand query with contextual information."""
        try:
            prompt = f"""
            Given this query: "{query}"

            Add contextual terms and background information to improve search results.
            Consider what additional context would help understand this query better.

            Contextually expanded query:
            """

            async with self.ollama_client:
                response = await self.ollama_client.generate(
                    prompt=prompt,
                    model="llama2",
                    max_tokens=50,
                    temperature=0.2
                )

            expanded = response.get('response', '').strip()
            return expanded if expanded else query

        except Exception:
            return query


# Global instance
query_understanding_service = QueryUnderstandingService()