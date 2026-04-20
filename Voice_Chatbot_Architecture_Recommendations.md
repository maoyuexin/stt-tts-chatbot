# Voice-Based Chatbot Architecture: User File Caching & Real-Time Audio

**Date:** November 7, 2025  
**Topic:** Microsoft Recommendations for Chatbot File Management and Real-Time Audio Models

---

## Executive Summary

This document provides Microsoft's recommendations for implementing:
1. **User file caching and memory** - Allowing users to see recent attachments when they log back in
2. **Real-time audio models** - Voice-based chatbot interactions using Azure OpenAI

The recommendations are based on Microsoft's official documentation and production-proven architectures, including the technology that powers OpenAI's ChatGPT.

---

## Table of Contents

1. [User File Caching Strategy](#1-user-file-caching-strategy)
2. [Comprehensive Cache Management by File Type](#2-comprehensive-cache-management-by-file-type)
3. [Session & Conversation History Management](#3-session--conversation-history-management)
4. [Real-Time Audio Model (Azure OpenAI)](#4-real-time-audio-model-azure-openai)
5. [Complete Architecture Recommendation](#5-complete-architecture-recommendation)
6. [Implementation Patterns](#6-implementation-patterns)
7. [Best Practices](#7-best-practices)
8. [Cost Optimization](#8-cost-optimization)
9. [Security & Compliance](#9-security--compliance)
10. [Reference Implementations](#10-reference-implementations)
11. [Additional Resources](#11-additional-resources)

---

## 1. User File Caching Strategy

### Primary Recommendation: Azure Cosmos DB

Microsoft recommends **Azure Cosmos DB** as the unified solution for chatbot memory and file management. This is the same technology that successfully enabled OpenAI's ChatGPT to scale dynamically with high reliability and low maintenance[^1].

#### Key Benefits

| Feature | Benefit |
|---------|---------|
| **Latency** | Single-digit millisecond response time |
| **Availability** | 99.999% SLA (< 5 minutes downtime/year) |
| **Indexing** | Automatic indexing without schema management |
| **Multi-modal** | Store metadata, embeddings, and conversation history together |
| **Scalability** | Global distribution with horizontal scaling |
| **Change Feed** | Real-time tracking of data changes |

#### Why Cosmos DB Over Other Databases?

**vs. In-Memory Databases:**
- Cosmos DB provides persistent storage while maintaining near-memory speeds
- Better for large-scale data that agents need to access

**vs. Relational Databases:**
- No rigid schemas - handles varied data modalities
- No manual partitioning/sharding required
- Better for fluid data structures in AI applications

**vs. Pure Vector Databases:**
- Provides transactional guarantees (ACID compliance)
- Higher availability (99.9% vs 99.999%)
- Multiple consistency levels (strong to eventual)
- More efficient resource usage (not entirely in-memory)

*Reference: [AI Agents in Azure Cosmos DB - Implementation Sample](https://learn.microsoft.com/en-us/azure/cosmos-db/ai-agents#implementation-sample)*

---

## 2. Comprehensive Cache Management by File Type

### Overview: The Three-Tier Caching Strategy

Effective cache management for chatbots involves a **three-tier approach** that balances performance, cost, and context window limitations:

```
┌─────────────────────────────────────────────────────────────┐
│              TIER 1: Metadata Cache (Hot)                   │
│  • Always in memory (Cosmos DB)                             │
│  • < 1ms access time                                        │
│  • File names, types, upload dates, summaries               │
│  • Small footprint (~1KB per file)                          │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         TIER 2: Processed Content Cache (Warm)              │
│  • Pre-processed, ready for LLM (Cosmos DB + Redis)        │
│  • 10-50ms access time                                      │
│  • Embeddings, extracted text, key insights                 │
│  • Medium footprint (~10-100KB per file)                    │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            TIER 3: Raw File Storage (Cold)                  │
│  • Original files (Azure Blob Storage)                      │
│  • 100-500ms access time                                    │
│  • Only accessed when full re-processing needed             │
│  • Large footprint (original file size)                     │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle:** Cache processed content, not raw files. The goal is to avoid re-processing files every time they're referenced in a conversation.

---

### Cache Strategy by File Type

#### 1. Audio Files (.wav, .mp3, .m4a, .flac)

**Challenge:** 
- Large file sizes (1-100MB per file)
- Expensive to process (speech-to-text costs ~$0.006/minute)
- Cannot fit directly into LLM context window

**Three-Tier Caching Approach:**

**TIER 1 - Metadata Cache (Always cached):**
```json
{
  "file_id": "audio-uuid-123",
  "file_name": "customer_call_2025-11-07.wav",
  "file_type": "audio/wav",
  "file_size": 25600000,
  "duration_seconds": 320,
  "upload_timestamp": "2025-11-07T10:30:00Z",
  "last_accessed": "2025-11-07T14:20:00Z",
  "blob_url": "https://storage.../customer_call.wav",
  "processing_status": "completed",
  "cache_status": {
    "tier1": true,
    "tier2": true,
    "tier2_expires_at": "2025-11-14T14:20:00Z"
  },
  "quick_summary": "5-minute customer support call about billing issue"
}
```

**TIER 2 - Processed Content Cache (Cached for 7-30 days):**
```json
{
  "file_id": "audio-uuid-123",
  "processed_content": {
    "transcript": "Full text transcription of the audio...",
    "transcript_with_timestamps": [
      {"start": 0.0, "end": 3.5, "text": "Hello, I'm calling about my bill..."},
      {"start": 3.5, "end": 8.2, "text": "I see a charge that I don't recognize..."}
    ],
    "speaker_diarization": {
      "speaker_1": "Customer",
      "speaker_2": "Agent"
    },
    "key_topics": ["billing", "dispute", "resolution"],
    "sentiment_analysis": {
      "overall": "negative_to_positive",
      "customer_satisfaction": 7
    },
    "action_items": [
      "Follow up on disputed charge within 2 business days",
      "Send confirmation email"
    ],
    "embedding_vector": [0.023, -0.154, 0.332, ...], // 1536 dimensions
    "token_count": 1450,
    "llm_ready_summary": "Customer called regarding unrecognized $250 charge..."
  },
  "processing_metadata": {
    "transcription_model": "whisper-1",
    "transcription_cost": 0.032,
    "processed_at": "2025-11-07T10:31:45Z",
    "processing_time_seconds": 12.3
  }
}
```

**TIER 3 - Raw File Storage:**
- Original .wav file in Azure Blob Storage (Hot tier for 30 days, then Cool tier)
- Only accessed if user requests to re-listen or re-process with different settings

**Why This Works:**
- **Avoid re-processing:** Transcription already done, saved in Tier 2
- **Fast context injection:** Pre-computed summary fits in context window
- **Cost savings:** No repeated Whisper API calls ($0.006/min × 5 min = $0.03 saved per access)
- **Semantic search:** Embedding vector enables "find similar calls" queries

**When to Use Each Tier:**
```python
def get_audio_content_for_llm(file_id: str, use_case: str):
    """Smart cache retrieval based on use case"""
    
    # TIER 1: Always start with metadata
    metadata = cosmos_db.get_item(file_id, partition_key="audio_files")
    
    if use_case == "list_recent_files":
        # Just show file name and quick summary (TIER 1 only)
        return {
            "name": metadata["file_name"],
            "summary": metadata["quick_summary"],
            "duration": f"{metadata['duration_seconds']}s"
        }
    
    elif use_case == "answer_question_about_file":
        # Use processed content (TIER 2)
        if metadata["cache_status"]["tier2"]:
            processed = cosmos_db.get_item(
                f"{file_id}_processed", 
                partition_key="processed_content"
            )
            return processed["processed_content"]["llm_ready_summary"]
        else:
            # Cache expired, re-process from TIER 3
            return reprocess_audio_file(metadata["blob_url"])
    
    elif use_case == "full_replay":
        # Download from TIER 3
        return download_blob(metadata["blob_url"])
```

**Cost Comparison:**

| Scenario | Without Tier 2 Cache | With Tier 2 Cache | Savings |
|----------|---------------------|-------------------|---------|
| First access | $0.032 (Whisper) | $0.032 (Whisper) + $0.0001 (storage) | $0 |
| Second access | $0.032 (re-transcribe) | $0.0003 (Cosmos read) | $0.0317 (99%) |
| 10 accesses/month | $0.32 | $0.032 + $0.003 = $0.035 | $0.285 (89%) |

---

#### 2. Video Files (.mp4, .mov, .avi, .webm)

**Challenge:**
- Very large file sizes (10MB-1GB+)
- Multiple processing steps (video → frames + audio → transcription + image analysis)
- Most expensive to process (GPT-4o vision ~$0.01/image, Whisper $0.006/min)

**Three-Tier Caching Approach:**

**TIER 1 - Metadata Cache:**
```json
{
  "file_id": "video-uuid-456",
  "file_name": "product_demo_2025-11-07.mp4",
  "file_type": "video/mp4",
  "file_size": 157286400,
  "duration_seconds": 180,
  "resolution": "1920x1080",
  "fps": 30,
  "upload_timestamp": "2025-11-07T09:00:00Z",
  "last_accessed": "2025-11-07T14:20:00Z",
  "blob_url": "https://storage.../product_demo.mp4",
  "thumbnail_url": "https://cdn.../thumbnail.jpg",
  "processing_status": "completed",
  "cache_status": {
    "tier1": true,
    "tier2": true,
    "tier2_expires_at": "2025-12-07T09:00:00Z"
  },
  "quick_summary": "3-minute product demo showing new features"
}
```

**TIER 2 - Processed Content Cache:**
```json
{
  "file_id": "video-uuid-456",
  "processed_content": {
    "audio_transcript": "Welcome to our product demo. Today we'll show you...",
    "transcript_with_timestamps": [...],
    
    "keyframe_analysis": [
      {
        "timestamp": 0.0,
        "image_url": "https://cdn.../keyframe_001.jpg",
        "description": "Title slide with product logo and version number",
        "detected_text": "Product v2.0 - New Features",
        "detected_objects": ["laptop", "logo", "text"]
      },
      {
        "timestamp": 15.3,
        "image_url": "https://cdn.../keyframe_002.jpg",
        "description": "Dashboard showing analytics charts and graphs",
        "detected_text": "Analytics Dashboard",
        "detected_objects": ["chart", "graph", "ui_elements"]
      }
    ],
    
    "scene_changes": [0.0, 15.3, 42.1, 87.5, 125.0, 165.2],
    
    "visual_summary": "Video shows product interface with focus on analytics dashboard, reporting features, and user management screens",
    
    "key_moments": [
      {
        "timestamp": 42.1,
        "title": "New Analytics Feature",
        "description": "Demonstrates real-time data visualization"
      }
    ],
    
    "combined_content": "This 3-minute video demonstrates [Product v2.0]. The presenter explains [audio transcript summary]. Visually, the video shows [keyframe descriptions]. Key features highlighted include: analytics dashboard, reporting, user management.",
    
    "embedding_vector": [0.123, -0.054, 0.432, ...],
    "token_count": 2850,
    "llm_ready_summary": "Product demo video showing v2.0 features..."
  },
  "processing_metadata": {
    "frames_extracted": 18,
    "frames_analyzed": 6,
    "transcription_cost": 0.018,
    "vision_analysis_cost": 0.06,
    "total_cost": 0.078,
    "processed_at": "2025-11-07T09:02:30Z",
    "processing_time_seconds": 145
  }
}
```

**TIER 3 - Raw File Storage:**
- Original .mp4 in Blob Storage (Cool tier after 7 days, Archive after 90 days)
- Keyframe images in CDN for quick preview
- Only re-process if user asks specific questions about frames not analyzed

**Processing Strategy:**
```python
async def process_video_smart_cache(video_file_path: str):
    """Process video with smart caching to minimize costs"""
    
    # 1. Extract audio track
    audio_track = extract_audio(video_file_path)
    
    # 2. Transcribe audio (cache this - expensive!)
    transcript = await azure_openai.audio.transcribe(
        model="whisper-1",
        file=audio_track
    )
    
    # 3. Detect scene changes (cache this - computational)
    scene_changes = detect_scene_changes(video_file_path)
    
    # 4. Extract keyframes at scene changes (not every frame!)
    keyframes = extract_keyframes_at_timestamps(
        video_file_path, 
        timestamps=scene_changes,
        max_frames=10  # Limit to control costs
    )
    
    # 5. Analyze keyframes with GPT-4o Vision (cache this - very expensive!)
    keyframe_analyses = []
    for frame in keyframes:
        analysis = await azure_openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this frame in detail"},
                    {"type": "image_url", "image_url": {"url": frame.url}}
                ]
            }]
        )
        keyframe_analyses.append(analysis)
    
    # 6. Create combined summary (cache this - derived from expensive operations)
    combined_summary = create_multimodal_summary(
        transcript=transcript,
        keyframe_analyses=keyframe_analyses
    )
    
    # 7. Generate embedding (cache this - used for semantic search)
    embedding = await azure_openai.embeddings.create(
        model="text-embedding-3-large",
        input=combined_summary
    )
    
    # 8. Store everything in TIER 2 cache
    await cosmos_db.upsert_item({
        "id": f"{video_id}_processed",
        "processed_content": {
            "audio_transcript": transcript,
            "keyframe_analysis": keyframe_analyses,
            "combined_content": combined_summary,
            "embedding_vector": embedding.data[0].embedding
        },
        "cache_expiry": datetime.now() + timedelta(days=30)
    })
    
    return combined_summary
```

**Cost Comparison:**

| Operation | Cost per Video | Without Cache (10 accesses) | With Cache (10 accesses) |
|-----------|---------------|----------------------------|-------------------------|
| Whisper transcription | $0.018 | $0.18 | $0.018 |
| GPT-4o Vision (6 frames) | $0.06 | $0.60 | $0.06 |
| Embeddings | $0.0001 | $0.001 | $0.0001 |
| Storage (30 days) | $0.002/month | $0.002 | $0.002 |
| **Total** | | **$0.783** | **$0.080** |
| **Savings** | | | **90% ($0.703)** |

---

#### 3. Document Files (.pdf, .docx, .pptx, .txt)

**Challenge:**
- Medium file sizes (100KB-50MB)
- Structured content requires parsing
- Long documents exceed context window (GPT-4o: 128K tokens)

**Three-Tier Caching Approach:**

**TIER 1 - Metadata Cache:**
```json
{
  "file_id": "doc-uuid-789",
  "file_name": "Q3_Financial_Report_2025.pdf",
  "file_type": "application/pdf",
  "file_size": 5242880,
  "page_count": 47,
  "upload_timestamp": "2025-11-05T08:00:00Z",
  "last_accessed": "2025-11-07T14:20:00Z",
  "blob_url": "https://storage.../Q3_Financial_Report.pdf",
  "processing_status": "completed",
  "cache_status": {
    "tier1": true,
    "tier2": true,
    "tier2_expires_at": "2025-12-05T08:00:00Z"
  },
  "quick_summary": "47-page quarterly financial report with revenue analysis"
}
```

**TIER 2 - Processed Content Cache:**
```json
{
  "file_id": "doc-uuid-789",
  "processed_content": {
    "full_text": "Q3 2025 Financial Report\n\nExecutive Summary\nRevenue increased by...",
    
    "chunked_content": [
      {
        "chunk_id": "chunk_001",
        "page_range": "1-2",
        "section": "Executive Summary",
        "content": "Revenue increased by 15% compared to Q3 2024...",
        "token_count": 450,
        "embedding_vector": [0.234, -0.123, ...]
      },
      {
        "chunk_id": "chunk_002",
        "page_range": "3-8",
        "section": "Revenue Analysis",
        "content": "Product line A contributed $5.2M in revenue...",
        "token_count": 890,
        "embedding_vector": [0.145, -0.089, ...]
      }
      // ... 15 more chunks
    ],
    
    "document_structure": {
      "table_of_contents": [
        {"section": "Executive Summary", "pages": "1-2"},
        {"section": "Revenue Analysis", "pages": "3-8"},
        {"section": "Expense Breakdown", "pages": "9-15"},
        {"section": "Appendices", "pages": "16-47"}
      ]
    },
    
    "extracted_tables": [
      {
        "page": 5,
        "table_id": "table_001",
        "description": "Quarterly revenue by product line",
        "structured_data": {
          "headers": ["Product", "Q3 2024", "Q3 2025", "Growth %"],
          "rows": [
            ["Product A", "$4.5M", "$5.2M", "15.6%"],
            ["Product B", "$3.2M", "$3.8M", "18.8%"]
          ]
        }
      }
    ],
    
    "extracted_figures": [
      {
        "page": 7,
        "figure_id": "fig_001",
        "caption": "Revenue trend Q1-Q3 2025",
        "image_url": "https://cdn.../fig_001.png",
        "description": "Line chart showing upward revenue trend"
      }
    ],
    
    "key_insights": [
      "Revenue up 15% YoY",
      "Product B shows strongest growth at 18.8%",
      "Operating expenses increased 8% due to expansion"
    ],
    
    "executive_summary": "Q3 2025 financial report shows strong performance with 15% revenue growth to $9M. Product B led growth at 18.8%. Operating expenses rose 8% due to planned expansion. Net profit increased 22% to $1.8M.",
    
    "document_embedding": [0.456, -0.234, ...],
    "total_tokens": 12500
  },
  "processing_metadata": {
    "extraction_tool": "azure-document-intelligence",
    "chunks_created": 17,
    "processing_cost": 0.008,
    "processed_at": "2025-11-05T08:01:20Z"
  }
}
```

**TIER 3 - Raw File Storage:**
- Original PDF in Blob Storage

**Smart Retrieval Strategy:**
```python
def get_document_content_for_llm(file_id: str, user_query: str):
    """
    Retrieve only relevant chunks, not entire document
    """
    
    # Get metadata (TIER 1)
    metadata = cosmos_db.get_item(file_id)
    
    if "what is this document about" in user_query.lower():
        # Use executive summary only (lightweight)
        processed = get_processed_content(file_id)
        return processed["executive_summary"]
    
    elif "revenue" in user_query.lower():
        # Vector search to find relevant chunks
        query_embedding = generate_embedding(user_query)
        
        relevant_chunks = vector_search(
            collection="document_chunks",
            query_vector=query_embedding,
            filter={"file_id": file_id},
            top_k=3
        )
        
        # Return only relevant chunks (3 chunks × 500 tokens = 1500 tokens)
        return "\n\n".join([chunk["content"] for chunk in relevant_chunks])
    
    else:
        # Semantic search across all chunks
        return semantic_chunk_retrieval(file_id, user_query)
```

**Why Chunking Matters:**
- **Context window limits:** Full document (12,500 tokens) might be too large
- **Relevance:** User usually needs specific sections, not entire document
- **Cost:** Pay only for tokens actually used
- **Speed:** Retrieve 3 chunks (1,500 tokens) vs. entire document (12,500 tokens)

**Token Cost Comparison:**

| Approach | Tokens Used | GPT-4o Cost | Response Time |
|----------|-------------|-------------|---------------|
| Send full document | 12,500 input | $0.125 | 3-5 seconds |
| Send relevant chunks (3) | 1,500 input | $0.015 | 1-2 seconds |
| **Savings** | **88% fewer tokens** | **88% cheaper** | **50% faster** |

---

#### 4. Image Files (.jpg, .png, .gif, .webp)

**Challenge:**
- Visual content requires GPT-4o Vision ($0.01 per image)
- No text to index directly
- Multiple images in a conversation can be expensive

**Three-Tier Caching Approach:**

**TIER 1 - Metadata Cache:**
```json
{
  "file_id": "image-uuid-321",
  "file_name": "product_screenshot.png",
  "file_type": "image/png",
  "file_size": 845632,
  "dimensions": "1920x1080",
  "upload_timestamp": "2025-11-07T11:00:00Z",
  "last_accessed": "2025-11-07T14:20:00Z",
  "blob_url": "https://storage.../product_screenshot.png",
  "thumbnail_url": "https://cdn.../thumb_product_screenshot.jpg",
  "processing_status": "completed",
  "cache_status": {
    "tier1": true,
    "tier2": true,
    "tier2_expires_at": "2025-12-07T11:00:00Z"
  },
  "quick_summary": "Screenshot of product dashboard showing analytics"
}
```

**TIER 2 - Processed Content Cache:**
```json
{
  "file_id": "image-uuid-321",
  "processed_content": {
    "vision_analysis": {
      "detailed_description": "The image shows a modern web dashboard with a dark theme. The main content area displays three analytics charts: a line graph showing user growth over 6 months, a pie chart breaking down user demographics, and a bar chart comparing product usage across different tiers. The left sidebar contains navigation menu items including Dashboard, Analytics, Users, and Settings.",
      
      "detected_objects": [
        {"object": "chart", "type": "line_graph", "confidence": 0.98},
        {"object": "chart", "type": "pie_chart", "confidence": 0.95},
        {"object": "chart", "type": "bar_chart", "confidence": 0.97},
        {"object": "ui_element", "type": "sidebar", "confidence": 0.99}
      ],
      
      "detected_text": [
        "Dashboard Analytics",
        "User Growth - Last 6 Months",
        "Demographics Breakdown",
        "Usage by Tier"
      ],
      
      "color_scheme": ["#1a1a1a", "#ffffff", "#4a90e2", "#f5a623"],
      
      "layout_analysis": "Dashboard layout with left sidebar navigation and main content area containing three visualization widgets arranged in a grid pattern",
      
      "answerable_questions": [
        "What is shown in this image?",
        "What type of dashboard is this?",
        "What charts are visible?",
        "What is the color scheme?",
        "What navigation options are available?"
      ]
    },
    
    "searchable_content": "dashboard analytics chart line graph pie chart bar chart user growth demographics usage sidebar navigation dark theme web interface",
    
    "embedding_vector": [0.678, -0.234, ...],
    
    "llm_ready_description": "This is a screenshot of a web analytics dashboard with a dark theme. It contains three main charts (line graph for user growth, pie chart for demographics, bar chart for usage tiers) and a navigation sidebar."
  },
  "processing_metadata": {
    "vision_model": "gpt-4o-2024-11-07",
    "vision_cost": 0.01,
    "processed_at": "2025-11-07T11:00:45Z"
  }
}
```

**TIER 3 - Raw File Storage:**
- Original high-res image in Blob Storage
- Thumbnail in CDN for quick preview

**Smart Image Handling:**
```python
async def handle_image_in_conversation(file_id: str, user_query: str):
    """
    Decide whether to send image to GPT-4o Vision or use cached description
    """
    
    # Get metadata
    metadata = cosmos_db.get_item(file_id)
    
    # Check if we have processed content
    processed = cosmos_db.get_item(f"{file_id}_processed")
    
    # Analyze user query
    if is_simple_question(user_query):
        # Questions like "What is this?" or "Describe this image"
        # Use cached description (no vision API call needed!)
        return processed["processed_content"]["llm_ready_description"]
    
    elif query_matches_cached_answers(user_query, processed["answerable_questions"]):
        # Question can be answered from cached analysis
        return extract_answer_from_cache(user_query, processed)
    
    else:
        # Complex or specific question - need to send image to GPT-4o Vision
        image_url = metadata["blob_url"]
        
        response = await azure_openai.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": user_query},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }]
        )
        
        return response.choices[0].message.content

def is_simple_question(query: str) -> bool:
    """Check if query is generic and can be answered from cache"""
    simple_patterns = [
        "what is this",
        "describe this",
        "what am i looking at",
        "what does this show",
        "explain this image"
    ]
    query_lower = query.lower()
    return any(pattern in query_lower for pattern in simple_patterns)
```

**Cost Savings Example:**

| Scenario | Without Cache | With Cache | Savings |
|----------|--------------|------------|---------|
| "What is this image?" (generic) | $0.01 (Vision API) | $0.0003 (Cosmos read) | 97% |
| "What charts are shown?" (cached) | $0.01 (Vision API) | $0.0003 (Cosmos read) | 97% |
| "What is the exact value at month 3?" (specific) | $0.01 (Vision API) | $0.01 (Vision API - cache miss) | 0% |
| **10 mixed queries** | **$0.10** | **$0.03** | **70%** |

---

### Unified Cache Management Strategy

#### Cache Invalidation Rules

```python
class CacheManager:
    """Unified cache management across all file types"""
    
    CACHE_DURATIONS = {
        "audio": timedelta(days=30),      # Transcripts rarely change
        "video": timedelta(days=30),      # Expensive to reprocess
        "document": timedelta(days=60),   # Static content
        "image": timedelta(days=90),      # Visual analysis stable
    }
    
    def should_invalidate_cache(self, file_metadata: dict) -> bool:
        """Determine if cache should be invalidated"""
        
        # Rule 1: Cache expired by time
        if datetime.now() > file_metadata["cache_status"]["tier2_expires_at"]:
            return True
        
        # Rule 2: Original file was modified
        if file_metadata["last_modified"] > file_metadata["last_processed"]:
            return True
        
        # Rule 3: User requests full reprocess
        if file_metadata.get("force_reprocess"):
            return True
        
        return False
    
    def get_content_for_llm(self, file_id: str, user_query: str) -> dict:
        """
        Main entry point for retrieving file content for LLM
        """
        
        # TIER 1: Always load metadata (fast, cheap)
        metadata = self.get_metadata(file_id)
        
        # Determine strategy based on query complexity
        if self.is_metadata_sufficient(user_query):
            # Simple query: "When did I upload this?"
            return {"source": "tier1", "content": metadata}
        
        # TIER 2: Try to use processed content
        if not self.should_invalidate_cache(metadata):
            processed = self.get_processed_content(file_id)
            
            if self.can_answer_from_cache(user_query, processed):
                return {"source": "tier2", "content": processed}
        
        # TIER 3: Need to reprocess from original file
        original_file = self.download_from_blob(metadata["blob_url"])
        processed = self.process_file(original_file, metadata["file_type"])
        
        # Update TIER 2 cache
        self.update_processed_cache(file_id, processed)
        
        return {"source": "tier3_reprocessed", "content": processed}
```

#### Redis for Hot Cache (Optional Tier 2A)

For frequently accessed files, add Redis between Cosmos DB and the application:

```python
import redis
from datetime import timedelta

class HotCacheLayer:
    """In-memory cache for hottest content"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host='your-redis.redis.cache.windows.net',
            port=6380,
            password='your-key',
            ssl=True
        )
    
    def get_hot_content(self, file_id: str) -> Optional[dict]:
        """Try to get from Redis first (< 1ms)"""
        cached = self.redis_client.get(f"processed:{file_id}")
        if cached:
            return json.loads(cached)
        return None
    
    def set_hot_content(self, file_id: str, content: dict, access_count: int):
        """Cache in Redis if file is frequently accessed"""
        if access_count > 5:  # Hot file threshold
            self.redis_client.setex(
                f"processed:{file_id}",
                timedelta(hours=1),  # Expire after 1 hour
                json.dumps(content)
            )
```

**Complete Retrieval Flow:**

```
User Query → Check Redis (Tier 2A) [< 1ms]
               ↓ (miss)
            Check Cosmos DB (Tier 2) [< 10ms]
               ↓ (miss or expired)
            Download from Blob (Tier 3) [100-500ms]
               ↓
            Process file [5-120 seconds]
               ↓
            Cache in Cosmos DB (Tier 2)
               ↓
            Cache in Redis if hot (Tier 2A)
               ↓
            Return to user
```

---

### Context Window Management

#### Problem: Files Don't Fit in Context Window

Even with caching, you need strategies to fit content into LLM context limits:

| Model | Context Window | Typical Usage |
|-------|---------------|---------------|
| GPT-4o | 128K tokens | ~300 pages of text |
| GPT-4o-mini | 128K tokens | ~300 pages of text |
| GPT-4-turbo | 128K tokens | ~300 pages of text |

#### Solution 1: Intelligent Chunking

```python
def intelligent_chunk_retrieval(file_id: str, user_query: str, max_tokens: int = 4000):
    """
    Retrieve only relevant chunks that fit in context window
    """
    
    # Generate embedding for user query
    query_embedding = generate_embedding(user_query)
    
    # Vector search for most relevant chunks
    relevant_chunks = cosmos_db.query(
        f"SELECT c.chunk_id, c.content, c.token_count, "
        f"VectorDistance(c.embedding_vector, @query_embedding) as similarity "
        f"FROM c WHERE c.file_id = @file_id "
        f"ORDER BY similarity DESC",
        parameters=[
            {"name": "@file_id", "value": file_id},
            {"name": "@query_embedding", "value": query_embedding}
        ]
    )
    
    # Pack chunks until we hit token limit
    selected_chunks = []
    total_tokens = 0
    
    for chunk in relevant_chunks:
        if total_tokens + chunk["token_count"] <= max_tokens:
            selected_chunks.append(chunk)
            total_tokens += chunk["token_count"]
        else:
            break
    
    return {
        "chunks": selected_chunks,
        "total_tokens": total_tokens,
        "coverage": f"{len(selected_chunks)} of {len(relevant_chunks)} relevant chunks"
    }
```

#### Solution 2: Map-Reduce for Large Documents

```python
async def analyze_large_document(file_id: str, user_query: str):
    """
    Map-Reduce pattern for documents that don't fit in one context window
    """
    
    # Get all chunks
    chunks = get_all_document_chunks(file_id)
    
    # MAP: Analyze each chunk independently
    chunk_analyses = []
    for chunk in chunks:
        analysis = await azure_openai.chat.completions.create(
            model="gpt-4o-mini",  # Use cheaper model for individual chunks
            messages=[{
                "role": "user",
                "content": f"Analyze this section for: {user_query}\n\nContent: {chunk['content']}"
            }]
        )
        chunk_analyses.append(analysis.choices[0].message.content)
    
    # REDUCE: Synthesize final answer from all chunk analyses
    final_answer = await azure_openai.chat.completions.create(
        model="gpt-4o",  # Use better model for final synthesis
        messages=[{
            "role": "user",
            "content": f"User asked: {user_query}\n\n"
                      f"Here are analyses from different sections of the document:\n\n"
                      f"{chr(10).join(chunk_analyses)}\n\n"
                      f"Provide a comprehensive answer:"
        }]
    )
    
    return final_answer.choices[0].message.content
```

---

### Monitoring & Optimization

#### Key Metrics to Track

```python
class CacheMetrics:
    """Track cache performance"""
    
    def __init__(self):
        self.app_insights = ApplicationInsightsClient()
    
    def track_cache_performance(self, file_id: str, operation: str):
        """Track cache hit/miss rates and costs"""
        
        metrics = {
            "cache_tier_used": "tier1|tier2|tier3",
            "response_time_ms": 0,
            "cost_usd": 0.0,
            "tokens_used": 0,
            "processing_required": False
        }
        
        self.app_insights.track_event("file_access", metrics)
```

**Target Metrics:**

| Metric | Target | Good | Needs Improvement |
|--------|--------|------|-------------------|
| Tier 2 cache hit rate | > 80% | > 70% | < 70% |
| Average response time | < 500ms | < 1s | > 1s |
| Cost per query | < $0.01 | < $0.05 | > $0.05 |
| Context window usage | < 50% | < 75% | > 75% |

---

### Summary: Cache Management Best Practices

✅ **Always cache metadata** (Tier 1) - Enable instant file listing and basic queries

✅ **Cache processed content** (Tier 2) - Avoid expensive re-processing (transcription, vision analysis, parsing)

✅ **Never cache raw files** in hot storage - Keep originals in cold Blob Storage

✅ **Use embeddings** - Enable semantic search without processing full content

✅ **Chunk strategically** - Balance between granularity and context

✅ **Monitor cache hit rates** - Optimize TTL based on access patterns

✅ **Implement cache warming** - Pre-process files asynchronously after upload

✅ **Use Redis for hot files** - Sub-millisecond access for frequently used content

✅ **Clean up expired caches** - Use Cosmos DB TTL feature

✅ **Track costs** - Measure savings from caching vs. re-processing

**The Golden Rule:** 
> **Cache the expensive operations (AI processing), not the cheap operations (file storage)**. A $0.03 transcription cached and accessed 100 times saves $2.97 (99% savings).

---

## 3. Session & Conversation History Management

### Enabling Chat History

Microsoft's Azure OpenAI Web App provides a reference implementation for persistent chat history and user file management[^2].

#### Architecture Pattern

```
User Session
├── Session ID (unique per user login)
├── Chat History (conversation turns)
├── File Metadata (recent attachments)
│   ├── File Name
│   ├── File Type (audio, pdf, docx, etc.)
│   ├── Upload Timestamp
│   ├── Last Accessed
│   ├── Blob Storage URL
│   └── Content Embeddings (for semantic search)
├── User Preferences
└── Access Permissions
```

#### Configuration Example

When deploying the Azure OpenAI Web App, enable chat history with these environment variables:

```bash
# Cosmos DB Configuration
AZURE_COSMOSDB_ACCOUNT="<your-cosmos-db-account>"
AZURE_COSMOSDB_DATABASE="db_conversation_history"
AZURE_COSMOSDB_CONTAINER="conversations"
AZURE_COSMOSDB_ENABLE_FEEDBACK="True"

# UI Configuration
UI_SHOW_CHAT_HISTORY_BUTTON="True"
```

#### Key Features Provided

✅ **Persistent Conversations** - Users see their history across sessions  
✅ **Automatic Ordering** - Newest to oldest conversation sorting  
✅ **User Isolation** - Each user only sees their own data  
✅ **Rename/Delete** - Users can manage their conversations  
✅ **Feedback Collection** - Thumbs up/down on responses  

*Reference: [Use the Azure OpenAI Web App - Enabling Chat History](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/use-web-app#enabling-chat-history-using-cosmos-db)*

### Session State Management

Microsoft's Bot Framework provides proven patterns for state management[^3]:

#### Three Types of State Buckets

| State Type | Scope | Use Case |
|------------|-------|----------|
| **User State** | Channel ID + User ID | User preferences, recent files, settings |
| **Conversation State** | Channel ID + Conversation ID | Current conversation context |
| **Private Conversation State** | All three IDs | User-specific data within group conversations |

#### Implementation with Cosmos DB

```python
from azure.cosmos import CosmosClient
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory

# Initialize Cosmos DB connection
client = CosmosClient(connection_string)
database = client.get_database_client("travel")
container = database.get_container_client("history")

# Create session-specific message history
def get_session_history(session_id: str):
    return MongoDBChatMessageHistory(
        database_name="chatbot",
        collection_name="conversation_history",
        connection_string=os.environ.get("MONGO_CONNECTION_STRING"),
        session_id=session_id
    )
```

*Reference: [Managing State - Bot Framework](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-concept-state)*

---

## 4. Real-Time Audio Model (Azure OpenAI)

### GPT-4o Realtime API

Microsoft offers the **GPT-4o Realtime API** specifically designed for low-latency, "speech in, speech out" conversational interactions[^4].

#### Supported Models

| Model | Version | Best For |
|-------|---------|----------|
| `gpt-4o-realtime-preview` | 2024-12-17 | High-quality voice interactions |
| `gpt-4o-mini-realtime-preview` | 2024-12-17 | Cost-effective voice applications |
| `gpt-realtime` | 2025-08-28 | Production voice assistants |
| `gpt-realtime-mini` | 2025-10-06 | Lightweight voice applications |

**Available Regions:** East US 2, Sweden Central  
**API Version:** 2025-04-01-preview

#### Connection Methods

1. **WebRTC** ⭐ (Recommended)
   - Lowest latency for client applications
   - Designed for real-time audio streaming
   - Built-in error correction and jitter handling
   - Peer-to-peer communication reduces latency

2. **WebSockets**
   - Server-to-server scenarios
   - When low latency is not critical
   - Easier integration with existing systems

3. **SIP**
   - Telephony system integration
   - Traditional phone system compatibility

*Reference: [Use the GPT Realtime API via WebRTC](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/realtime-audio-webrtc)*

### Real-Time Audio Capabilities

#### Voice Activity Detection (VAD)

The Realtime API offers two VAD modes:

**1. Server VAD (`server_vad`)** - Automatic speech detection
```json
{
  "turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,
    "prefix_padding_ms": 300,
    "silence_duration_ms": 200,
    "create_response": true
  }
}
```

**2. Semantic VAD (`semantic_vad`)** - Context-aware turn detection
- Detects when user has finished speaking based on semantic meaning
- Reduces interruptions during natural speech
- Better for complex conversations

#### Audio Transcription

Built-in Whisper transcription provides:
- Real-time speech-to-text conversion
- Support for multiple languages
- Transcript storage alongside audio

```json
{
  "input_audio_transcription": {
    "model": "whisper-1"
  }
}
```

#### Session Configuration Example

```json
{
  "type": "session.update",
  "session": {
    "voice": "alloy",
    "instructions": "You are a helpful voice assistant...",
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16",
    "input_audio_transcription": {
      "model": "whisper-1"
    },
    "turn_detection": {
      "type": "semantic_vad",
      "threshold": 0.5,
      "silence_duration_ms": 200,
      "create_response": true
    },
    "modalities": ["audio", "text"]
  }
}
```

#### Response Interruption Handling

Users can interrupt the assistant mid-response:
- Server produces audio faster than real-time
- Client can send `conversation.item.truncate` to stop playback
- Synchronizes server understanding with client playback
- Deletes unheard text to maintain context accuracy

*Reference: [GPT Realtime API for Speech and Audio](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/realtime-audio)*

---

## 5. Complete Architecture Recommendation

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   User Devices                              │
│    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│    │   Web App    │  │  Mobile App  │  │   Phone      │   │
│    │  (WebRTC)    │  │  (WebRTC)    │  │   (SIP)      │   │
│    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
└───────────┼──────────────────┼──────────────────┼───────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Microsoft Entra ID         │
                │  (Authentication)           │
                └──────────────┬──────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Azure OpenAI               │
                │  GPT-4o Realtime API        │
                │  ┌────────────────────────┐ │
                │  │ Speech-to-Text         │ │
                │  │ (Whisper)              │ │
                │  ├────────────────────────┤ │
                │  │ LLM Inference          │ │
                │  │ (GPT-4o)               │ │
                │  ├────────────────────────┤ │
                │  │ Text-to-Speech         │ │
                │  │ (Neural Voices)        │ │
                │  └────────────────────────┘ │
                └──────────────┬──────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
     ┌──────▼────────┐  ┌──────▼────────┐  ┌────▼──────────┐
     │ Azure Cosmos  │  │ Azure Blob    │  │ Azure AI      │
     │     DB        │  │   Storage     │  │    Search     │
     │               │  │               │  │               │
     │ • Sessions    │  │ • Audio Files │  │ • File Search │
     │ • Chat Hist   │  │ • Documents   │  │ • Vector      │
     │ • File Meta   │  │ • Images      │  │   Search      │
     │ • User Prefs  │  │ • Videos      │  │ • Semantic    │
     │ • Embeddings  │  │               │  │   Search      │
     └───────────────┘  └───────────────┘  └───────────────┘
```

### Data Flow

1. **User Authentication** → Microsoft Entra ID validates user
2. **Session Creation** → Generate unique session ID, store in Cosmos DB
3. **Voice Input** → WebRTC streams audio to GPT-4o Realtime API
4. **Transcription** → Whisper converts speech to text
5. **Context Retrieval** → Query Cosmos DB for:
   - Recent conversation history
   - User's recent files metadata
   - Relevant file content from Blob Storage
6. **LLM Processing** → GPT-4o generates response with context
7. **Voice Output** → Text-to-speech creates audio response
8. **History Storage** → Save interaction in Cosmos DB
9. **File Management** → Update "last accessed" timestamps

---

## 6. Implementation Patterns

### Pattern 1: File Metadata Storage

Store file references in Cosmos DB for fast retrieval:

```json
{
  "id": "file-uuid-12345",
  "partition_key": "user-abc",
  "user_id": "user-abc",
  "session_id": "session-xyz-789",
  "file_metadata": {
    "file_name": "quarterly-report.pdf",
    "file_type": "pdf",
    "file_size": 2457600,
    "mime_type": "application/pdf",
    "upload_timestamp": "2025-11-07T10:30:00Z",
    "last_accessed": "2025-11-07T14:20:00Z"
  },
  "storage": {
    "blob_url": "https://mystorageaccount.blob.core.windows.net/files/quarterly-report.pdf",
    "container": "user-files",
    "blob_name": "user-abc/quarterly-report.pdf"
  },
  "ai_metadata": {
    "content_summary": "Q3 2025 financial report showing 15% revenue growth...",
    "embedding_vector": [0.023, -0.154, 0.332, ...],
    "extracted_entities": ["Q3 2025", "revenue", "growth", "financial"],
    "content_indexed": true
  },
  "access_control": {
    "owner": "user-abc",
    "shared_with": [],
    "is_public": false
  }
}
```

### Pattern 2: Recent Files Query

Retrieve user's recent files efficiently:

```python
import os
from azure.cosmos import CosmosClient, PartitionKey

# Initialize Cosmos DB client
client = CosmosClient.from_connection_string(
    os.environ["COSMOS_CONNECTION_STRING"]
)
database = client.get_database_client("chatbot_db")
container = database.get_container_client("user_files")

def get_recent_files(user_id: str, limit: int = 10):
    """Get user's most recently accessed files"""
    query = """
        SELECT 
            c.id,
            c.file_metadata.file_name,
            c.file_metadata.file_type,
            c.file_metadata.last_accessed,
            c.storage.blob_url,
            c.ai_metadata.content_summary
        FROM c 
        WHERE c.user_id = @user_id 
        ORDER BY c.file_metadata.last_accessed DESC
        OFFSET 0 LIMIT @limit
    """
    
    parameters = [
        {"name": "@user_id", "value": user_id},
        {"name": "@limit", "value": limit}
    ]
    
    items = list(container.query_items(
        query=query,
        parameters=parameters,
        partition_key=user_id
    ))
    
    return items

# Usage
recent_files = get_recent_files("user-abc", limit=10)
```

### Pattern 3: Session Management

Implement session management similar to M365:

```python
import uuid
from datetime import datetime, timedelta

def create_user_session(user_id: str, cosmos_container):
    """Create a new session for user"""
    session_id = str(uuid.uuid4())
    
    session_doc = {
        "id": session_id,
        "partition_key": user_id,
        "user_id": user_id,
        "session_type": "voice_chat",
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "conversation_history": [],
        "recent_files": [],
        "preferences": {
            "voice": "alloy",
            "language": "en-US"
        }
    }
    
    cosmos_container.create_item(session_doc)
    return session_id

def get_session_context(session_id: str, cosmos_container):
    """Retrieve session context including recent files"""
    try:
        session = cosmos_container.read_item(
            item=session_id,
            partition_key=session_id
        )
        
        # Get recent files for this user
        user_id = session["user_id"]
        recent_files = get_recent_files(user_id, limit=5)
        
        return {
            "session": session,
            "recent_files": recent_files
        }
    except Exception as e:
        print(f"Session not found: {e}")
        return None
```

### Pattern 4: Integrating Real-Time Audio with File Context

```python
from azure.openai import AzureOpenAI
import asyncio

async def voice_chat_with_context(session_id: str, audio_stream):
    """Handle voice chat with file context"""
    
    # 1. Get session context
    context = get_session_context(session_id, cosmos_container)
    
    # 2. Format recent files for LLM context
    files_context = "\n".join([
        f"- {file['file_name']} (accessed {file['last_accessed']}): {file['content_summary']}"
        for file in context["recent_files"]
    ])
    
    # 3. Configure Realtime API session
    session_config = {
        "type": "session.update",
        "session": {
            "instructions": f"""You are a helpful voice assistant. 
            
The user has recently worked with these files:
{files_context}

You can reference these files in your responses when relevant.""",
            "voice": "alloy",
            "input_audio_transcription": {"model": "whisper-1"},
            "turn_detection": {
                "type": "semantic_vad",
                "threshold": 0.5,
                "silence_duration_ms": 200
            },
            "modalities": ["audio", "text"]
        }
    }
    
    # 4. Stream audio to Realtime API
    async with AzureOpenAI.realtime_connect(
        api_version="2025-04-01-preview"
    ) as client:
        # Send session configuration
        await client.send(session_config)
        
        # Stream audio and handle responses
        async for audio_chunk in audio_stream:
            await client.send({
                "type": "input_audio_buffer.append",
                "audio": audio_chunk
            })
```

*Reference: [AI Agents in Azure Cosmos DB - Implementation](https://learn.microsoft.com/en-us/azure/cosmos-db/ai-agents#implementation-of-ai-agents)*

---

## 7. Best Practices

### Session Management

✅ **Use Microsoft Entra ID** for authentication and user identity  
✅ **Implement user-scoped sessions** - Each user has isolated data  
✅ **Store session ID securely** - Use `httpOnly` cookies or secure storage  
✅ **Set appropriate timeouts** - 30 minutes for active sessions, 24 hours for inactive  
✅ **Clean up expired sessions** - Use Cosmos DB TTL feature  

### File Management

✅ **Recent files retention** - Consider 30-90 day auto-cleanup  
✅ **Lazy loading** - Load metadata first, content on-demand  
✅ **Implement file size limits** - 50MB per file for optimal performance  
✅ **Use content hashing** - Deduplicate identical files  
✅ **Index file content** - Enable full-text search via Azure AI Search  

### Audio Processing

✅ **Choose appropriate model** - `gpt-realtime-mini` for most use cases  
✅ **Enable transcription** - Store transcripts for compliance/audit  
✅ **Handle interruptions gracefully** - Allow users to stop mid-response  
✅ **Monitor latency** - Target < 200ms for real-time feel  
✅ **Implement fallback** - Switch to text if audio quality is poor  

### Performance Optimization

✅ **Use Cosmos DB's partition keys wisely** - Partition by `user_id`  
✅ **Enable Cosmos DB caching** - Integrated cache for hot data  
✅ **Implement semantic caching** - 80% faster for similar queries[^5]  
✅ **Use Azure CDN** - Cache static file content globally  
✅ **Batch operations** - Use bulk APIs for multiple file updates  

*Reference: [Prompt Caching](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/prompt-caching)*

---

## 8. Cost Optimization

### Cosmos DB Pricing Strategies

| Mode | Best For | Savings |
|------|----------|---------|
| **Serverless** | Dev/test, variable workloads | Pay per request |
| **Provisioned** | Production, predictable traffic | Stable pricing |
| **Reserved Capacity** | Long-term production | Up to 65% savings |

### Azure OpenAI Optimization

**Prompt Caching Benefits:**
- Reduces token costs for repeated context
- 80% faster response times
- Automatically enabled for GPT-4o models
- Cached tokens billed at discount rate

**Model Selection:**
- `gpt-4o-mini-realtime`: Most cost-effective for voice
- `gpt-4o-realtime`: Higher quality, higher cost
- Monitor usage with Azure Monitor

### Storage Optimization

**Azure Blob Storage Tiers:**
- **Hot tier**: Frequently accessed files (< 30 days)
- **Cool tier**: Infrequently accessed files (30-90 days)
- **Archive tier**: Long-term storage (> 90 days)

**Example Cost Structure:**
```
For 1000 users, 10 files each, 1MB average file size:
- Blob Storage (Hot): ~$20/month for 10GB
- Cosmos DB (Provisioned 1000 RU/s): ~$65/month
- GPT-4o-mini-realtime: ~$0.60 per 1M tokens
- Total estimate: ~$100-200/month (excluding audio processing)
```

*Reference: [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)*

---

## 9. Security & Compliance

### Data Protection

| Feature | Implementation |
|---------|----------------|
| **Encryption at Rest** | Automatic in Cosmos DB and Blob Storage |
| **Encryption in Transit** | TLS 1.2+ for all connections |
| **Data Residency** | Choose Azure regions for compliance |
| **Backup & Recovery** | Automatic backups every 4 hours |

### Authentication & Authorization

**Microsoft Entra ID Integration:**
```python
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient

# Use managed identity (no keys in code)
credential = DefaultAzureCredential()
client = CosmosClient(
    url="https://<account>.documents.azure.com:443/",
    credential=credential
)
```

**Role-Based Access Control (RBAC):**

| Role | Permissions | Assign To |
|------|-------------|-----------|
| `Cosmos DB Data Reader` | Read documents | Application |
| `Cosmos DB Data Contributor` | Read/Write documents | Application |
| `Storage Blob Data Reader` | Read blobs | Application |
| `Cognitive Services OpenAI User` | Call OpenAI API | Application |

### Compliance Certifications

Azure Cosmos DB supports:
- ✅ HIPAA/HITECH
- ✅ SOC 1, 2, 3
- ✅ ISO 27001
- ✅ GDPR compliance
- ✅ FedRAMP

### Prompt Injection Defense

Azure OpenAI includes built-in protections:
- Malicious pattern detection
- Content filtering
- Sandboxed execution
- Metaprompting safeguards

*Reference: [Security for Microsoft 365 Copilot](https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-ai-security)*

---

## 10. Reference Implementations

### 1. Azure OpenAI Web App with Chat History

**Repository:** [microsoft/sample-app-aoai-chatGPT](https://github.com/microsoft/sample-app-aoai-chatGPT)

**Features:**
- Cosmos DB integration for chat history
- User authentication with Entra ID
- File upload and management
- Customizable UI
- Azure AI Search integration

**Quick Start:**
```bash
# Clone repository
git clone https://github.com/microsoft/sample-app-aoai-chatGPT.git

# Configure environment
cp .env.sample .env
# Edit .env with your Azure credentials

# Deploy to Azure
azd up
```

### 2. RAG + Real-Time Audio Sample

**Repository:** [Azure-Samples/aisearch-openai-rag-audio](https://github.com/Azure-Samples/aisearch-openai-rag-audio)

**Features:**
- Voice interface with document grounding
- GPT-4o Realtime API integration
- Azure AI Search for document retrieval
- WebRTC implementation

**Use Case:** Voice-based RAG application where users can ask questions about documents using speech.

### 3. AI Travel Agent with Cosmos DB

**Repository:** [jonathanscholtes/Travel-AI-Agent-React-FastAPI-and-Cosmos-DB-Vector-Store](https://github.com/jonathanscholtes/Travel-AI-Agent-React-FastAPI-and-Cosmos-DB-Vector-Store)

**Features:**
- Complete AI agent implementation
- Cosmos DB for memory system
- Session management
- Conversation history
- React frontend + FastAPI backend

**Architecture Highlights:**
- Multi-agent system with LangChain
- Vector embeddings in Cosmos DB
- Document storage and retrieval
- Session-based memory

*Reference: [AI Agents in Azure Cosmos DB - Implementation Sample](https://learn.microsoft.com/en-us/azure/cosmos-db/ai-agents#implementation-sample)*

---

## 11. Additional Resources

### Official Documentation

#### Chat History & Session Management
- [Use the Azure OpenAI Web App](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/use-web-app)
- [Enabling Chat History Using Cosmos DB](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/use-web-app#enabling-chat-history-using-cosmos-db)
- [Managing State - Bot Framework](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-concept-state)
- [Save User and Conversation Data](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-howto-v4-state)

#### AI Agents & Memory Systems
- [AI Agents in Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/ai-agents)
- [Building a Robust AI Agent Memory System](https://learn.microsoft.com/en-us/azure/cosmos-db/ai-agents#building-a-robust-ai-agent-memory-system)
- [Cosmos DB Vector Database](https://learn.microsoft.com/en-us/azure/cosmos-db/vector-database)

#### Real-Time Audio
- [GPT Realtime API Overview](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/realtime-audio)
- [Realtime API via WebRTC](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/realtime-audio-webrtc)
- [Realtime API via WebSockets](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/realtime-audio-websockets)
- [Realtime Audio Quickstart](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/realtime-audio-quickstart)

#### Performance & Optimization
- [Prompt Caching](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/prompt-caching)
- [Caching Overview - API Management](https://learn.microsoft.com/en-us/azure/api-management/caching-overview)
- [Azure Cosmos DB Performance Tips](https://learn.microsoft.com/en-us/azure/cosmos-db/performance-tips)

#### Security & Compliance
- [Security for Microsoft 365 Copilot](https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-ai-security)
- [Microsoft 365 Copilot Architecture](https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-architecture)
- [Data Protection in Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/database-security)

### Video Resources

- [OpenAI's ChatGPT Service Architecture](https://www.youtube.com/watch?v=6IIUtEFKJec&t) - How ChatGPT uses Cosmos DB
- [Azure OpenAI Real-Time Audio Demo](https://aka.ms/openai-realtime-demo)

### Community Resources

- [Microsoft Tech Community - Copilot Blog](https://techcommunity.microsoft.com/blog/microsoft365copilotblog/)
- [Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/)
- [Azure AI Samples Repository](https://github.com/Azure-Samples)

### Support & Contact

- **Azure Support:** [https://azure.microsoft.com/support/](https://azure.microsoft.com/support/)
- **OpenAI API Support:** [https://help.openai.com/](https://help.openai.com/)
- **Service Trust Portal:** [https://servicetrust.microsoft.com/](https://servicetrust.microsoft.com/)

---

## Appendix: Comparison with M365 Copilot

Your customer mentioned wanting capabilities similar to M365 Copilot. Here's how the recommended architecture compares:

| Feature | M365 Copilot | Recommended Architecture |
|---------|--------------|--------------------------|
| **User File Memory** | ✅ Microsoft Graph | ✅ Cosmos DB + Blob Storage |
| **Session Persistence** | ✅ Across devices | ✅ User-scoped sessions |
| **Recent Attachments** | ✅ Automatic tracking | ✅ Custom implementation |
| **Voice Interaction** | ✅ Real-time audio | ✅ GPT-4o Realtime API |
| **Context Awareness** | ✅ Microsoft 365 data | ✅ Custom data sources |
| **Security** | ✅ Entra ID | ✅ Entra ID + RBAC |
| **Scalability** | ✅ Global | ✅ Global (Cosmos DB) |
| **Customization** | ⚠️ Limited | ✅ Fully customizable |

**Key Advantages of Custom Implementation:**
- Full control over data and behavior
- Support for custom file types and workflows
- Integration with existing systems
- Flexible pricing models
- Custom UI/UX

*Reference: [Microsoft 365 Copilot Architecture](https://learn.microsoft.com/en-us/copilot/microsoft-365/microsoft-365-copilot-architecture)*

---

## Footnotes

[^1]: Azure Cosmos DB successfully enabled OpenAI's ChatGPT service to scale dynamically with high reliability and low maintenance. Source: [AI Agents in Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/ai-agents)

[^2]: The Azure OpenAI Web App provides a reference implementation with Cosmos DB integration for chat history. Source: [Use the Azure OpenAI Web App](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/use-web-app#enabling-chat-history-using-cosmos-db)

[^3]: Microsoft's Bot Framework provides proven patterns for managing user state, conversation state, and private conversation state. Source: [Managing State](https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-concept-state)

[^4]: The GPT-4o Realtime API is part of the GPT-4o model family that supports low-latency, "speech in, speech out" conversational interactions. Source: [GPT Realtime API](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/realtime-audio)

[^5]: Semantic caching can improve query performance by 80% and reduce LLM inference costs. Source: [Prompt Caching](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/prompt-caching)

---

**Document Version:** 1.0  
**Last Updated:** November 7, 2025  
**Author:** Technical Architecture Team  
**Review Status:** Ready for Customer Discussion
